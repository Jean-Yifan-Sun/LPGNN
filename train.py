import logging
import os
import time
import torch
from argparse import ArgumentParser
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning import Trainer, seed_everything
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from torch_geometric.transforms import GDC
from datasets import get_available_datasets, GraphDataModule
from privacy import get_available_mechanisms
from models import NodeClassifier
from transforms import RandomWalkExpand, Privatize
from utils import TermColors
from itertools import product


def train_and_test(dataset, method, eps, args, repeats, output_dir):
    for run in range(repeats):
        params = {
            'task': 'node',
            'dataset': dataset.name,
            'method': method,
            'eps': eps,
            'run': run
        }

        params_str = ' | '.join([f'{key}={val}' for key, val in params.items()])
        print(TermColors.FG.green + params_str + TermColors.reset)

        save_dir = os.path.join(output_dir, 'node', dataset.name, method, str(eps))
        logger = TensorBoardLogger(save_dir=save_dir, name=None)

        checkpoint_path = os.path.join('checkpoints', save_dir)
        checkpoint_callback = ModelCheckpoint(monitor='val_loss', filepath=checkpoint_path)

        params = vars(args)
        # log_learning_curve = run == 0 and (method == 'raw' or method == 'pgc')
        log_learning_curve = True
        model = NodeClassifier(**params, log_learning_curve=log_learning_curve)

        trainer = Trainer.from_argparse_args(
            args=args,
            precision=32,
            gpus=int(args.device == 'cuda' and torch.cuda.is_available()),
            max_epochs=500,
            checkpoint_callback=checkpoint_callback,
            logger=logger,
            log_save_interval=500,
            weights_summary=None,
            deterministic=True,
            progress_bar_refresh_rate=10,
            early_stop_callback=EarlyStopping(patience=500),
        )

        privatize = Privatize(method=method, eps=eps)
        dataset.add_transform(privatize)
        trainer.fit(model=model, datamodule=dataset)
        trainer.test(datamodule=dataset, ckpt_path='best', verbose=True)


def batch_train_and_test(args):
    dataset = GraphDataModule(name=args.dataset, normalize=(0, 1), device=args.device)

    if args.rw:
        rw = RandomWalkExpand(walk_length=200, p=0.1)
        dataset.add_transform(rw)

    if args.gdc:
        gdc = GDC(self_loop_weight=1, normalization_in='sym', normalization_out='sym',
                  diffusion_kwargs=dict(method='ppr', alpha=0.05, eps=1e-4),
                  sparsification_kwargs=dict(method='threshold', avg_degree=100), exact=False)
        dataset.add_transform(gdc)
        args.normalize = False

    if 'raw' in args.methods:
        configs = [('raw', 0)]
        configs += list(product(set(args.methods) - {'raw'}, set(args.epsilons) - {0.0}))
    else:
        configs = product(args.methods, args.epsilons)

    for method, eps in configs:
        train_and_test(
            dataset=dataset,
            method=method,
            eps=eps,
            args=args,
            repeats=args.repeats,
            output_dir=args.output_dir
        )


def main():
    seed_everything(12345)
    logging.getLogger("lightning").setLevel(logging.ERROR)
    logging.captureWarnings(True)

    parser = ArgumentParser()
    parser.add_argument('-d', '--dataset', type=str, choices=get_available_datasets(), required=True,
                        help='The dataset to train on. One of "citeseer", "cora", "elliptic", "flickr", and "twitch".'
                        )
    parser.add_argument('-m', '--methods', nargs='+', choices=get_available_mechanisms() + ['raw'], required=True,
                        help='The list of mechanisms to perturb node features. '
                             'Can choose "raw" to use original features, or "pgc" for Private Graph Convolution, '
                             '"pm" for Piecewise Mechanism, and "lm" for Laplace Mechanism, '
                             'as local differentially private algorithms.'
                        )
    parser.add_argument('-e', '--eps', nargs='*', type=float, dest='epsilons', default=[0],
                        help='The list of epsilon values for LDP mechanisms. The values must be greater than zero. '
                             'The "raw" method does not support this options.'
                        )
    parser.add_argument('-r', '--repeats', type=int, default=1,
                        help='The number of repeating the experiment. Default is 1.'
                        )
    parser.add_argument('-o', '--output-dir', type=str, default='./results',
                        help='The path to store the results. Default is "./results".'
                        )
    parser.add_argument('--gdc', action='store_true', default=False)
    parser.add_argument('--rw', action='store_true', default=False)
    parser.add_argument('--device', type=str, default='cuda', choices=['cpu', 'cuda'],
                        help='The device used for the training. Either "cpu" or "cuda". Default is "cuda".'
                        )
    parser = NodeClassifier.add_module_specific_args(parser)
    args = parser.parse_args()

    # check if eps > 0 for LDP methods
    if len(set(args.methods) & set(get_available_mechanisms())) > 0:
        if min(args.epsilons) <= 0:
            parser.error('LDP methods require eps > 0.')

    print(args)
    start = time.time()
    batch_train_and_test(args)
    end = time.time()
    print('\nTotal time spent:', end - start, 'seconds.\n\n')


if __name__ == '__main__':
    main()
