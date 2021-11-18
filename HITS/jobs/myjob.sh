#!/bin/bash
#SBATCH -o output/myjob_%j.out
#SBATCH -N 16
#SBATCH -n 256
#SBATCH --threads-per-core=1
#SBATCH -t 24:00:00
#SBATCH --gres=gpu:2

module load Python/3.8.2-GCCcore-9.3.0
module load CUDA/11.0.2-GCC-9.3.0
module load CUDAcore/11.0.2

pip install --user pipenv
# pipenv --rm
# pipenv --python 3.8
pipenv install datetime matplotlib numpy pathlib tensorflow
pipenv install
pipenv run python ./myapp.py > output/myapp_output.txt

