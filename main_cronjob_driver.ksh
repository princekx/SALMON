#!/bin/ksh -l
module load scitools
#export PYTHONPATH=/net/home/h03/hadpx/MJO:$PYTHONPATH

# 1. doing the new MJO dashboard
/home/h03/hadpx/bin/spice_mjo /home/h03/hadpx/MJO/Monitoring_new/MJO/main_mogreps.py
/home/h03/hadpx/bin/spice_mjo /home/h03/hadpx/MJO/Monitoring_new/MJO/main_glosea.py

# 2. Cold MOGREPS_ColdSurge_monitor
/usr/bin/sbatch --time=30 --ntasks=16 --mem=40G --output=cs_new.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_mogreps.py
/usr/bin/sbatch --time=30 --ntasks=16 --mem=40G --output=cs_new.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_glosea.py

# 3. Equatorial waves stuff
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=eqwaves_new.log --partition=rhel7 /net/home/h03/hadpx/MJO/Monitoring_new/EQWAVES/main_mogreps.py 00
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=eqwaves_new.log --partition=rhel7 /net/home/h03/hadpx/MJO/Monitoring_new/EQWAVES/main_mogreps.py 06
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=eqwaves_new.log --partition=rhel7 /net/home/h03/hadpx/MJO/Monitoring_new/EQWAVES/main_mogreps.py 12
/usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=eqwaves_new.log --partition=rhel7 /net/home/h03/hadpx/MJO/Monitoring_new/EQWAVES/main_mogreps.py 18

4. BSISO stuff
/usr/bin/sbatch --time=30 --ntasks=1 --mem=10G --output=cs_new.log --partition=rhel7 /net/home/h03/hadpx/MJO/Monitoring_new/BSISO/main_bsiso.py


# OLD stuff
# 1. doing the MJO stuff
/home/h03/hadpx/bin/spice /home/h03/hadpx/MJO/Monitoring/mjo/analysis/retrieve_check_for_last10days.py
/home/h03/hadpx/bin/spice /home/h03/hadpx/MJO/Monitoring/mjo/main_mjo_job.py

# 2. doing the EqWaves stuff
/home/h03/hadpx/bin/spice1 /home/h03/hadpx/MJO/Monitoring/eqwaves/main_wave_job.py


# 3. Doing cold surge stuff
/home/h03/hadpx/bin/spice1 /home/h03/hadpx/MJO/Monitoring/mogreps_cold_surge/MOGREPS_ColdSurge_monitor.py
