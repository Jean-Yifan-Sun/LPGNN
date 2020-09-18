#################################################################################################
###################################### ERROR ESTIMATION #########################################
#################################################################################################

python error.py -d cora elliptic facebook github twitch -m gm mbm -e 0.5 1 2 4 -k 1 2 4 8 -a mean



#################################################################################################
##################################### NODE CLASSIFICATION #######################################
#################################################################################################

################### CORA ####################
### DPGNN
python train.py -d cora -m mbm -e 0.5 1 2 4 -k 1 2 4 8 16 32 64 -a mean --lr 0.01 --wd 0.01 --dp 0 -r 10
### GCN+GM
python train.py -d cora -m gm -e 0.5 1 2 4 -k 1 -a gcn --lr 0.01 --wd 0.01 --dp 0 -r 10
### GCN
python train.py -d cora -m raw -k 1 2 4 8 16 32 64 -a gcn --lr 0.01 --wd 0.01 --dp 0 -r 10


################# ELLIPTIC ##################
### DPGNN
python train.py -d elliptic -m mbm -e 0.5 1 2 4 -k 1 2 4 8 16 32 64 -a mean --lr 0.01 --wd 0 --dp 0.5 -r 10
### GCN+GM
python train.py -d elliptic -m gm -e 0.5 1 2 4 -k 1 -a gcn --lr 0.01 --wd 0 --dp 0.5 -r 10
### GCN
python train.py -d elliptic -m raw -k 1 2 4 8 16 32 64 -a gcn --lr 0.01 --wd 0 --dp 0.5 -r 10


################# FACEBOOK ##################
### DPGNN
python train.py -d facebook -m mbm -e 0.5 1 2 4 -k 1 2 4 8 16 32 64 -a mean --lr 0.01 --wd 0.001 --dp 0.5 -r 10
### GCN+GM
python train.py -d facebook -m gm -e 0.5 1 2 4 -k 1 -a gcn --lr 0.01 --wd 0.001 --dp 0.5 -r 10
### GCN
python train.py -d facebook -m raw -k 1 2 4 8 16 32 64 -a gcn --lr 0.01 --wd 0.001 --dp 0.5 -r 10


################## GITHUB ###################
### DPGNN
python train.py -d github -m mbm -e 0.5 1 2 4 -k 1 2 4 8 16 32 64 -a mean --lr 0.01 --wd 0 --dp 0.5 -r 10
### GCN+GM
python train.py -d github -m gm -e 0.5 1 2 4 -k 1 -a gcn --lr 0.01 --wd 0 --dp 0.5 -r 10
### GCN
python train.py -d github -m raw -k 1 2 4 8 16 32 64 -a gcn --lr 0.01 --wd 0 --dp 0.5 -r 10


################## TWITCH ###################
### DPGNN
python train.py -d twitch -m mbm -e 0.5 1 2 4 -k 1 2 4 8 16 32 64 -a mean --lr 0.001 --wd 0.01 --dp 0.5 -r 10
### GCN+GM
python train.py -d twitch -m gm -e 0.5 1 2 4 -k 1 -a gcn --lr 0.001 --wd 0.01 --dp 0.5 -r 10
### GCN
python train.py -d twitch -m raw -k 1 2 4 8 16 32 64 -a gcn --lr 0.001 --wd 0.01 --dp 0.5 -r 10
