import os
import sys
import uuid

import torch
from torch.optim import SGD, Adam
from tqdm.auto import tqdm

from utils import colored_text


class Trainer:
    def __init__(
            self,
            optimizer:      dict(help='optimization algorithm', choices=['sgd', 'adam']) = 'adam',
            learning_rate:  dict(help='learning rate') = 0.01,
            weight_decay:   dict(help='weight decay (L2 penalty)') = 0,
            max_epochs:     dict(help='maximum number of training epochs') = 1000,
            device:         dict(help='desired device for training', choices=['cpu', 'cuda']) = 'cuda',
            checkpoint:     dict(help='disable model checkpointing', option='--disable-checkpoint',
                                 action='store_false', dest='checkpoint') = True,
            logger = None,
            **kwargs
    ):
        self.optimizer = optimizer
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.device = device
        self.checkpoint = checkpoint
        self.logger = logger
        self.model = None

        if checkpoint:
            os.makedirs('checkpoints', exist_ok=True)
            self.checkpoint_path = os.path.join('checkpoints', f'{uuid.uuid1()}.pt')

        if not torch.cuda.is_available():
            print(colored_text('CUDA is not available, falling back to CPU', color='red'))
            self.device = 'cpu'

    def configure_optimizer(self, model):
        Optim = {'sgd': SGD, 'adam': Adam}[self.optimizer]
        optimizer = Optim(model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        return optimizer

    def fit(self, model, data):
        self.model = model.to(self.device)
        data = data.to(self.device)
        optimizer = self.configure_optimizer(model)

        best_val_loss = float('inf')
        epoch_progbar = tqdm(range(1, self.max_epochs + 1), desc='Epoch: ', leave=False, position=1, file=sys.stdout)

        epoch = None
        try:
            for epoch in epoch_progbar:
                train_metrics = self._train(data, optimizer)
                train_metrics['train_loss'] = train_metrics['train_loss'].item()

                val_metrics = self._validation(data)
                val_loss = val_metrics['val_loss']

                if self.logger:
                    self.logger.log({**train_metrics, **val_metrics}, step=epoch)

                if self.checkpoint and val_loss < best_val_loss:
                    best_val_loss = val_loss
                    torch.save(self.model.state_dict(), self.checkpoint_path)

                # display metrics on progress bar
                postfix = {**train_metrics, **val_metrics}
                epoch_progbar.set_postfix(postfix)
        except KeyboardInterrupt:
            pass

        if self.logger:
            self.logger.log({'train_epochs': epoch})
        return self.model

    def _train(self, data, optimizer):
        self.model.train()
        optimizer.zero_grad()
        metrics = self.model.training_step(data)
        loss = metrics['train_loss']
        loss.backward()
        optimizer.step()
        return metrics

    @torch.no_grad()
    def _validation(self, data):
        self.model.eval()
        return self.model.validation_step(data)

    @torch.no_grad()
    def test(self, data):
        if self.checkpoint:
            self.model.load_state_dict(torch.load(self.checkpoint_path))

        self.model.eval()
        metrics = self.model.test_step(data)
        return metrics
