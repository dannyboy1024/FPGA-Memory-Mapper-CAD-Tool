
# FPGA-logical-to-physical-memory-mapper
ECE1756 course assignment. A logical-to-physical memory mapper using a Next-Fit bin-packing algorithm for a Stratix-IV-like architecture in Python

The mapping tool is written in a python script named mapper.py
The RAM mapping file is basic.txt
The number of circuits is assumed to always be 69

There are two ways to run the script.

1)  For a Stratix-IV-like architecture, please run: 
	python mapper.py

2)  For other architectures (including Stratix-IV-like architecture), please run:
	python mapper.py <memType1>,<memType2>,…,<memTypeN> <maxWidth1>,<maxWidth2>,…,<maxWidthN> <LB/BRAM ratio1>,<LB/BRAM ratio2>,…,<LB/BRAM ratioN>, <% LB supporting LUTRAM> for N types of memories. 

	memType := log(BRAM size). If it’s a LUTRAM, memType := 18
	
	maxWidth can be any number that’s powers of 2. If it’s a LUTRAM, maxWidth is a placeholder.
	
	LB/BRAM ratio can be any positive integer values. If it’s a LUTRAM, LB/BRAM ratio must be set to 1
	
	% LB supporting LUTRAM can be any value from 0.0 to 1.0, inclusive. If LUTRAM is not used, set it to 1.0
	
	Only memories of size from 1k to 128k are allowed to use.
	

Examples: 

1) 
Type1: 1k BRAM, maxWidth = 4bits, LBs/BRAM = 2
Type2: 2k BRAM, maxWidth = 8bits, LBs/BRAM = 4
Type3: 16k BRAM, maxWidth = 16bits, LBs/BRAM =50
Command: python mapper.py 10,11,14 4,8,16 2,4,50 1.0
Checker command for reference: ./checker -b 1024 4 2 1 -b 2048 8 4 1 -b 16384 16 50 1 -t logical_rams.txt logic_block_count.txt basic.txt

2)
Type1: 4k BRAM, maxWidth = 16bit, LBs/BRAM = 20
Type2: LUTRAM (30% LBs supporting LUTRAM)
Command: python mapper.py 12,18 16,-1 20,1 0.3
Check command for reference: ./checker -b 4096 16 20 1 -l 1 1 -t logical_rams.txt logic_block_count.txt basic.txt
	

