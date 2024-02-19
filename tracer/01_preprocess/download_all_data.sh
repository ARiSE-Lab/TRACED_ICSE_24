# download and extract the Project CodeNet dataset
wget https://dax-cdn.cdn.appdomain.cloud/dax-project-codenet/1.0.0/Project_CodeNet.tar.gz
# only unzip C programs
tar -xf Project_CodeNet.tar.gz --exclude='Project_CodeNet/data/*' && \
  tar -xf Project_CodeNet.tar.gz --wildcards 'Project_CodeNet/data/p*/C/*'
# optional: unzip other data
# tar zxf Project_CodeNet.tar.gz

# extract the CodeNet input/output dataset
python 01_preprocess/convert_sample_input_output_full_to_files.py
