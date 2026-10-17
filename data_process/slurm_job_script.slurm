#!/bin/bash

#Submit this script with: sbatch thefilename

#SBATCH --job-name=fwm_dataprocess   ##name that will show up in the queue
#SBATCH --output=/scratch/%u/%x-%N-%j.out   ##filename of the output
#SBATCH --error=/scratch/%u/%x-%N-%j.err   ##filename of the error output
#SBATCH --nodes=1  ##number of nodes to use
#SBATCH --ntasks=1  ##number of tasks to run
#SBATCH --time=0-3:00:00  ##time for analysis (day-hour:min:sec)
#SBATCH --cpus-per-task=48  ##the number of threads the code will use
#SBATCH --mem=2048GB  ##memory allocation per node
#SBATCH --partition bigmem  ##the partition to run in
#SBATCH --mail-user acard@gmu.edu  ##your email address
#SBATCH --mail-type BEGIN ## slurm will email you when your job starts
#SBATCH --mail-type END  ##slurm will email you when your job ends
#SBATCH --mail-type FAIL  ##slurm will email you when your job fails


## Commands to Load Modules:
module load gnu10
module load python/3.10.1-5r
source /home/acard/fwm_process/bin/activate



## Load modules, insert code, and run your programs here.
python3 process_bags_anymal.py -d anymal -i /scratch/acard/anymal/ -o /scratch/acard/processed_data_10hz/anymal --parallel
python3 process_bags.py -d scand -i /scratch/acard/SCAND/ -o /scratch/acard/processed_data_10hz/scand --parallel
python3 process_bags.py -d tartan_drive_2 -i /scratch/acard/tartan2 -o /scratch/acard/processed_data_10hz/tartan2 --parallel
python3 process_bags.py -d tartan_drive_1 -i /scratch/acard/tartan1 -o /scratch/acard/processed_data_10hz/tartan1 --parallel
python3 process_bags.py -d rellis_3d -i /scratch/acard/rellis -o /scratch/acard/processed_data_10hz/rellis --parallel
python3 process_bags.py -d sub_t_tunnel -i /scratch/acard/sub_t/Tunnel -o /scratch/acard/processed_data_10hz/subt_tunnel --parallel
python3 process_bags.py -d botanic_garden -i /scratch/acard/botanic_garden -o /scratch/acard/processed_data_10hz/botanic_garden --parallel
python3 process_bags.py -d gnd -i /scratch/acard/GND -o /scratch/acard/processed_data_10hz/gnd --parallel
