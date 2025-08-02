
# FPGA-logical-to-physical-memory-mapper
ECE1756 course assignment. A logical-to-physical memory mapper implemented with a Next-Fit bin-packing algorithm for a Stratix-IV-like architecture in Python.  
It outputs basic.txt, which is the RAM mapping file.  
The number of circuits is assumed to always be 69  

## User instructions
For a Stratix-IV-like architecture, run **python mapper.py**  
For any architectures (including Stratix-IV-like architecture), please see the two examples below.  

### Example 1)
Type1: 1k BRAM, maxWidth = 4bits, LBs/BRAM = 2  
Type2: 2k BRAM, maxWidth = 8bits, LBs/BRAM = 4  
Type3: 16k BRAM, maxWidth = 16bits, LBs/BRAM =50  
**python mapper.py 10,11,14 4,8,16 2,4,50 1.0**  
Run: ./checker -b 1024 4 2 1 -b 2048 8 4 1 -b 16384 16 50 1 -t logical_rams.txt logic_block_count.txt basic.txt to get detailed area usage.  
### Example 2)
Type1: 4k BRAM, maxWidth = 16bit, LBs/BRAM = 20  
Type2: LUTRAM (30% LBs supporting LUTRAM)  
**python mapper.py 12,18 16,-1 20,1 0.3**  
Run ./checker -b 4096 16 20 1 -l 1 1 -t logical_rams.txt logic_block_count.txt basic.txt to get detailed area usage.  
	

