#!/bin/ksh -l
module load scitools

yesterday=$(date -d "yesterday" '+%Y-%m-%d')

echo $yesterday
# 1. doing the new MJO dashboard
/usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/mjo_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_mogreps.py $yesterday
echo /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/mjo_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_mogreps.py $yesterday

/usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/mjo_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_glosea.py $yesterday
echo /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/mjo_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_glosea.py $yesterday

# 2. Cold MOGREPS_ColdSurge_monitor
/usr/bin/sbatch --time=300 --ntasks=16 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/cs_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_mogreps.py $yesterday
/usr/bin/sbatch --time=300 --ntasks=16 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/cs_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_glosea.py $yesterday

# 3. Equatorial waves stuff
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/eqwaves_new_mogreps_${yesterday}_00.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 00
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/eqwaves_new_mogreps_${yesterday}_06.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 06
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/eqwaves_new_mogreps_${yesterday}_12.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 12
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/scratch/hadpx/SEA_monitoring/temp_log/eqwaves_new_mogreps_${yesterday}_18.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 18

#4. BSISO stuff
/usr/bin/sbatch --time=30 --ntasks=1 --mem=10G --output=/scratch/hadpx/SEA_monitoring/temp_log/bsiso_new_${yesterday}.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/BSISO/main_bsiso.py $yesterday


# OLD stuff
# 1. doing the MJO stuff
/home/h03/hadpx/bin/spice /home/h03/hadpx/MJO/Monitoring/mjo/analysis/retrieve_check_for_last10days.py
/home/h03/hadpx/bin/spice /home/h03/hadpx/MJO/Monitoring/mjo/main_mjo_job.py

# 2. doing the EqWaves stuff
/home/h03/hadpx/bin/spice1 /home/h03/hadpx/MJO/Monitoring/eqwaves/main_wave_job.py


# 3. Doing cold surge stuff
/home/h03/hadpx/bin/spice1 /home/h03/hadpx/MJO/Monitoring/mogreps_cold_surge/MOGREPS_ColdSurge_monitor.py
