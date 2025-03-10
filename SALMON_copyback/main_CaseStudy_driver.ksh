#!/bin/ksh -l
module load scitools

#yesterday=$(date -d "yesterday" '+%Y-%m-%d')
# List of dates
dates=("2020-05-06" "2020-05-13" "2023-07-13" "2023-07-20" "2023-07-21" "2023-07-22" "2023-07-24" "2023-07-25" "2023-07-26" "2023-07-27" "2023-07-28") # Add more dates as needed

# Loop through each date and run the sbatch command
for yesterday in "${dates[@]}"
do
  echo $yesterday
  # 1. doing the new MJO dashboard
  /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/tmp/hadpx/mjo_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_mogreps.py $yesterday
  echo /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/tmp/hadpx/mjo_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_mogreps.py $yesterday

  /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/tmp/hadpx/mjo_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_glosea.py $yesterday
  echo /usr/bin/sbatch --time=360 --ntasks=4 --mem=40G --output=/tmp/hadpx/mjo_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/MJO/main_glosea.py $yesterday

  # 2. Cold MOGREPS_ColdSurge_monitor
  /usr/bin/sbatch --time=300 --ntasks=16 --mem=40G --output=/tmp/hadpx/cs_new_mogreps_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_mogreps.py $yesterday
  /usr/bin/sbatch --time=300 --ntasks=16 --mem=40G --output=/tmp/hadpx/cs_new_glosea_${yesterday}.log --partition=rhel7 /home/h03/hadpx/MJO/Monitoring_new/COLDSURGE/main_glosea.py $yesterday

  # 3. Equatorial waves stuff
  /usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/tmp/hadpx/eqwaves_new_mogreps_${yesterday}_00.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 00
  /usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/tmp/hadpx/eqwaves_new_mogreps_${yesterday}_06.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 06
  /usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/tmp/hadpx/eqwaves_new_mogreps_${yesterday}_12.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 12
  /usr/bin/sbatch --time=360 --ntasks=8 --mem=40G --output=/tmp/hadpx/eqwaves_new_mogreps_${yesterday}_18.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/EQWAVES/main_mogreps.py $yesterday 18

  #4. BSISO stuff
  /usr/bin/sbatch --time=30 --ntasks=1 --mem=10G --output=/tmp/hadpx/bsiso_new_${yesterday}.log --partition=rhel7 /home/users/prince.xavier/MJO/Monitoring_new/BSISO/main_bsiso.py $yesterday

done