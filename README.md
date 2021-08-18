# healcheck
pip3 install psutil

1.cd json-c && mkdir build && cmake -DCMAKE_INSTALL_PREFIX=../../install .. && make -j -s &&　make install

2.cd $PWD && make -j -s && make install

###### 2.1 invoke healthcheck.update_ruleid_processid(ruleid,processid) within every camera+alg+processid


3.python script/healthcheck.py dothework
