from abc import abstractmethod

import torch
from pytorch_lightning import Trainer
from pytorch_lightning.loggers import LightningLoggerBase, rank_zero_only
from torch_geometric.utils import degree
from tsnecuda import TSNE

from gnn import GCNConv, GConvMixedDP
from models import GCNClassifier, Node2VecClassifier, GCNLinkPredictor, Node2VecLinkPredictor, transform_features

params = {
    'nodeclass': {
        'gcn': {
            'params': {
                'hidden_dim': 16,
                'weight_decay': 5e-4,
                'lr': 0.01
            },
            'epochs': 200,
        },
        'node2vec': {
            'params': {
                'embedding_dim': 64,
                'walk_length': 20,
                'context_size': 10,
                'walks_per_node': 10,
                'batch_size': 128,
                'lr': 0.01
            },
            'epochs': 100,
        }
    },
    'linkpred': {
        'gcn': {
            'epochs': 200,
            'params': {
                'hidden_dim': 128,
                'output_dim': 64,
                'dropout': 0,
                'lr': 0.01
            },
        },
        'node2vec': {
            'params': {
                'embedding_dim': 64,
                'walk_length': 20,
                'context_size': 10,
                'walks_per_node': 10,
                'batch_size': 128,
                'lr': 0.01
            },
            'epochs': 100,
        }
    }
}


class ResultLogger(LightningLoggerBase):
    @property
    def experiment(self):
        return self

    @rank_zero_only
    def log_metrics(self, metrics, step=None):
        if 'test_result' in metrics:
            # noinspection PyAttributeOutsideInit
            self.result = metrics['test_result']

    @rank_zero_only
    def log_hyperparams(self, parameters): pass

    @property
    def name(self): return 'ResultLogger'

    @property
    def version(self): return 0.1


class Task:
    @staticmethod
    def task_name(): raise NotImplementedError

    def __init__(self, dataset, model_name, feature, epsilon, priv_dim):
        self.dataset = dataset
        self.model_name = model_name
        self.feature = feature
        self.epsilon = epsilon
        self.priv_dim = priv_dim if self.feature == 'priv' else 0

    @abstractmethod
    def run(self): pass


class LearningTask(Task):

    @abstractmethod
    def get_model(self): pass

    def run(self, **train_args):
        logger = ResultLogger()
        model = self.get_model()
        trainer = Trainer(logger=logger, **train_args)
        trainer.fit(model)
        trainer.test()
        return logger.result


class NodeClassification(LearningTask):
    task_name = 'nodeclass'

    def get_model(self):
        if self.model_name == 'gcn':
            return GCNClassifier(
                dataset=self.dataset,
                feature=self.feature,
                priv_dim=self.priv_dim,
                epsilon=self.epsilon,
                **params['nodeclass']['gcn']['params']
            )
        else:
            return Node2VecClassifier(
                dataset=self.dataset,
                **params['nodeclass']['node2vec']['params']
            )


class LinkPrediction(LearningTask):
    task_name = 'linkpred'

    def get_model(self):
        if self.model_name == 'gcn':
            return GCNLinkPredictor(
                dataset=self.dataset,
                feature=self.feature,
                priv_dim=self.priv_dim,
                epsilon=self.epsilon,
                **params['nodeclass']['gcn']['params']
            )
        else:
            return Node2VecLinkPredictor(
                dataset=self.dataset,
                **params['nodeclass']['node2vec']['params']
            )


class ErrorEstimation(Task):
    @staticmethod
    def task_name():
        return 'errorest'

    def __init__(self, dataset, model_name, feature, epsilon, priv_dim):
        assert model_name == 'gcn' and feature == 'priv'
        super().__init__(dataset, model_name, feature, epsilon, priv_dim)
        data = self.dataset[0].to('cuda')
        delta = data.delta.clone()
        delta[delta == 0] = 1  # avoid inf and nan
        self.delta = delta
        gcnconv = GCNConv().to('cuda')
        self.gc = gcnconv(data.x, data.edge_index)

    @torch.no_grad()
    def run(self):
        data = self.dataset[0].to('cuda')
        data = transform_features(data, self.feature)
        model = GConvMixedDP(
            priv_dim=self.priv_dim,
            epsilon=self.epsilon,
            alpha=data.alpha,
            delta=data.delta
        ).to('cuda')
        gc_hat = model(data.x, data.edge_index)
        diff = (self.gc - gc_hat) / self.delta
        error = torch.norm(diff, p=1, dim=1) / diff.shape[1]
        deg = self.get_degree(data)
        return list(zip(error.cpu().numpy(), deg.cpu().numpy()))

    @staticmethod
    def get_degree(data):
        row, col = data.edge_index
        return degree(row, data.num_nodes)


class VisualizeEmbedding(LinkPrediction):
    @staticmethod
    def task_name():
        return 'visual'

    def __init__(self, dataset, model_name, feature, epsilon, priv_dim):
        assert model_name == 'gcn' and feature == 'priv'
        super().__init__(dataset, model_name, feature, epsilon, priv_dim)

    def run(self, **train_args):
        model = self.get_model()
        trainer = Trainer(**train_args)
        trainer.fit(model)
        z = model(self.dataset[0])
        return TSNE(n_components=2).fit_transform(z.cpu().numpy())
