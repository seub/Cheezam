!/bin/bash
#SBATCH -o myjob_%j.out
#SBATCH -N 4
#SBATCH -n 64
#SBATCH --threads-per-core=1
#SBATCH -t 24:00:00
#SBATCH --gres=gpu:2
 
module load Python/3.8.2-GCCcore-9.3.0
module load CUDA/11.0.2-GCC-9.3.0
module load SciPy-bundle/2020.03-foss-2020a-Python-3.8.2
 
python3 ./test_app.py > output/console_output.txt
