#!/bin/bash
#SBATCH -o output/myjob_%j.out
#SBATCH -N 1
#SBATCH -n 20
#SBATCH --threads-per-core=1
#SBATCH -t 24:00:00

# module load Python/3.8.2-GCCcore-9.3.0

pip install --user pipenv
# pipenv --rm
# pipenv --python 3.8
pipenv install datetime matplotlib numpy pathlib tensorflow
pipenv install
pipenv run python ./myapp.py > output/myapp_output.txt

