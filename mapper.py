import sys
import os
from os import path
import re
import math
import functools


NUM_CIRCUITS = 69
NUM_DIFF_BRAM_SIZE = 18 # 2^0, 2^1, 2^2, ... , 2^17, LB
LB = NUM_DIFF_BRAM_SIZE
STRATIX_IV = len(sys.argv)==1

class architecture_T():
    def __init__(self):
        self.maxWidthMp = {} # define the maximum width for each physical mem type
        self.ratioMp = {} # define the #physical mem type blocks / #LBs ratio
        self.typeMp = {} # define the type number for each physical mem type
        self.LUTRAMRatioLimit = 1.0 # Assume all the LBs can be used as LUTRAMs by default
        if STRATIX_IV:
            self.maxWidthMp[LB] = -1 # LB --> It's a don't-care. Defined separately in the genPhysicalRams function
            self.maxWidthMp[13] = 32 # 8k --> 32-bit word, 
            self.maxWidthMp[17] = 128 # 128k --> 128-bit word
            self.ratioMp[LB] = 1 #LB --> 1:1. 
            self.ratioMp[13] = 10 #8k --> 1:10
            self.ratioMp[17] = 300 #128k --> 1:300
            self.typeMp[LB] = 1
            self.typeMp[13] = 2
            self.typeMp[17] = 3
            self.LUTRAMRatioLimit = 0.5
        else:    
            memTypes = [int(s) for s in sys.argv[1].split(',')]
            maxWidths = [int(s) for s in sys.argv[2].split(',')]
            ratios = [int(s) for s in sys.argv[3].split(',')]
            LUTRamRationLimit = float(sys.argv[4])
            for memTypeIdx in range(1,len(memTypes)+1):
                memType = memTypes[memTypeIdx-1]
                self.typeMp[memType] = memTypeIdx
            for memType, memTypeIdx in self.typeMp.items():
                self.maxWidthMp[memType] = maxWidths[memTypeIdx-1]
                self.ratioMp[memType] = ratios[memTypeIdx-1]
            self.LUTRAMRatioLimit = LUTRamRationLimit
        
class logicalRam_T():
    def __init__(self, ramID, mode, depth, width):
        self.ramID = ramID
        self.mode = mode
        self.depth = depth
        self.width = width
        self.size = depth * width
    def printLogicRam(self):
        print('RAM'+str(self.ramID))
        print('Mode: '+self.mode, 'Depth: '+str(self.depth), 'Width: '+str(self.width), 'Size: '+str(self.size))

class physicalRam_T():
    def __init__(self, depth, width, sizeExp):
        self.depth = depth
        self.width = width
        self.sizeExp = sizeExp
            
class circuit_T():
    def __init__(self):
        self.logicalRams = []
        self.sortedLogicalRams = []
        self.numLB = 0
    def sortlogicalRams(self):
        def cmp(r1,r2):
            return -1 if r1.size>r2.size or (r1.size==r2.size and r1.depth>r2.depth) else 1
        self.sortedLogicalRams = sorted(self.logicalRams, key=functools.cmp_to_key(cmp))
    def printCircuit(self):
        for logicalRam in self.sortedLogicalRams:
            logicalRam.printLogicRam()
        print('Num logic blocks: ', self.numLB)

class mapping_T():
    def __init__(self, area, logicalRam, phyRam, s, p, numMuxes):
        self.area = area
        self.logicalRam = logicalRam
        self.phyRam = phyRam
        self.s = s
        self.p = p
        self.numMuxes = numMuxes
    

def genPhysicalRams(maxWidthMp):
    # generate different configurations for all choosen physical memories
    # group them as per their size
    # the last group are LUTRAMs
    physicalRams = [[] for i in range(NUM_DIFF_BRAM_SIZE+1)]
    for sizeExp in maxWidthMp:
        if sizeExp==LB:
            # append the two types of LUTRAMs
            physicalRams[sizeExp].append(physicalRam_T(64, 10, LB))
            physicalRams[sizeExp].append(physicalRam_T(32, 20, LB))
        else:
            # append all the configurations of BRAMs with the same size
            size = 1<<sizeExp
            for widthExp in range(NUM_DIFF_BRAM_SIZE):
                width = 1<<widthExp
                if width>maxWidthMp[sizeExp]: break
                depth = size//width
                physicalRams[sizeExp].append(physicalRam_T(depth, width, sizeExp))
    return physicalRams

def genCircuits(logicalRam_filePath, logicBlock_filePath):
    # get the circuits from the logical ram file
    circuits = [circuit_T() for i in range(NUM_CIRCUITS)]
    f = open(logicalRam_filePath, 'r')
    cnt = 0
    for line in f:
        if cnt>1:
            [circuitID,ramID,mode,depth,width] = line.replace('\n','',1).split()
            circuitID = int(circuitID)
            ramID = int(ramID)
            depth = int(depth)
            width = int(width)
            circuits[circuitID].logicalRams.append(logicalRam_T(ramID,mode,depth,width))
        cnt += 1
    f = open(logicBlock_filePath, 'r')
    cnt = 0
    for line in f:
        if cnt>0:
            [circuitID, numLB] = line.replace('\n','',1).split()
            numLB = int(numLB)
            circuitID = int(circuitID)
            circuits[circuitID].numLB = numLB
        cnt += 1
    
    # sort the logical rams 
    for circuit in circuits:
        circuit.sortlogicalRams()
    return circuits

def getResourceUsage(phyRam, logicalRam):
    # get logical ram info
    ld = logicalRam.depth
    lw = logicalRam.width
    mode = logicalRam.mode
    # compute resource usage
    d = phyRam.depth
    w = phyRam.width
    s = (ld-1)//d+1
    p = (lw-1)//w+1

    if s>16: 
        return False, -1, -1, -1 # Too many rams in series, too slow...
    numMuxes = ((s if s>2 else s-1) if mode!='ROM' else 0) + (0 if s==1 else (lw * (1 if s<=4 else 1+(s-1)//4+1)))
    numMuxes = 2*numMuxes if mode=='TrueDualPort' else numMuxes
    return True, s, p, numMuxes

def getArea(numPhyRams, phyRam, numMuxes, maxWidthMp):
    area = 0
    if phyRam.sizeExp != LB:
        bits = 1<<phyRam.sizeExp
        area += numPhyRams * (9000 + 5 * bits + 90 * math.sqrt(bits) + 1200 * maxWidthMp[phyRam.sizeExp])
    else:
        area += numPhyRams * 40000
    area += numMuxes/10.0 * 35000
    return area

def genCircuitMapping(generalSetup, circuit, physicalRams, phyID):

    # Keep track of the resources available or used
    srcMp = {}
    sinkMp = {}
    srcMp[LB] = circuit.numLB
    sinkMp[LB] = (circuit.numLB, 0.0)
    for phyRamType in generalSetup.typeMp:
        if phyRamType==LB: continue
        srcMp[phyRamType] = circuit.numLB // generalSetup.ratioMp[phyRamType]
        sinkMp[phyRamType] = 0.0

    # Generate mappings for each logical ram
    logicalRams = circuit.sortedLogicalRams
    mappings = [''] * len(logicalRams)
    for ramIdx in range(len(logicalRams)):
        
        # Get logical ram info
        logicalRam = logicalRams[ramIdx]
        mode = logicalRam.mode

        # Check if the logical ram can fit into the current "bin"
        possibleMappings = []
        for phyRamType in generalSetup.typeMp:
            if mode=='TrueDualPort' and phyRamType==LB: continue # Can't implement TrueDualPort rams using LUTRAMs
            sameTypePhyRams = physicalRams[phyRamType]
            for i in range(len(sameTypePhyRams)):
                if mode=='TrueDualPort' and i==len(sameTypePhyRams)-1: continue # Can't reach largest width under TrueDualPort mode

                # Compute resource usage
                phyRam = sameTypePhyRams[i]
                isLegalMapping, s, p, numMuxes = getResourceUsage(phyRam, logicalRam)
                if not isLegalMapping: continue

                # Compute area
                area = getArea(s*p, phyRam, numMuxes, generalSetup.maxWidthMp)
                possibleMappings.append(mapping_T(area,logicalRam,phyRam,s,p,numMuxes))
        
        # Rank the resource usage in ascending area order
        possibleMappings = sorted(possibleMappings, key = lambda x : x.area)
        if len(possibleMappings)==0:
            print('No legal mapping is found')
            sys.exit()

        # Iterate through the mappings in ascending area order
        # Check if there is a mapping that can fit in the current "bin"
        canFitCurrentBin = False
        possibleUpdatedSrcSinkMps = []
        chosenMapping = ''
        for mapping in possibleMappings:
            
            # Additional physical resources required
            phyRamType = mapping.phyRam.sizeExp
            numPhyRam = mapping.s * mapping.p
            numLB = (mapping.numMuxes / 10.0)

            # Calculate number of logic blocks and physical ram blocks required
            numLBUsed = sinkMp[LB][0]
            numLUTRAMUsed = sinkMp[LB][1]
            if phyRamType==LB:
                minRequiredLB = ((numLUTRAMUsed + numPhyRam) / generalSetup.LUTRAMRatioLimit)
                actualRequiredLB = numLBUsed + numLB + numLUTRAMUsed + numPhyRam
                requiredLB = max(minRequiredLB, actualRequiredLB)
                availLB = srcMp[LB]
                if availLB >= requiredLB:
                    canFitCurrentBin = True
                    sinkMp[LB] = (numLBUsed + numLB, numLUTRAMUsed + numPhyRam)
                    chosenMapping = mapping
                    break
                # Get the updated sinkMp
                updSinkMp = {}
                for srcType in sinkMp:
                    if srcType==LB:
                        updSinkMp[srcType] = (numLBUsed + numLB, numLUTRAMUsed + numPhyRam)
                    else:
                        updSinkMp[srcType] = sinkMp[srcType]
                # Get the updated srcMp with extra LBs added
                updSrcLB = requiredLB
                updSrcMp = {}
                for srcType in srcMp:
                    updSrcMp[srcType] = max(srcMp[srcType], updSrcLB // (generalSetup.ratioMp[srcType] if srcType!=LB else 1))
                # Calculate number of extra logic blocks needed
                extraLB = updSrcLB - availLB
                possibleUpdatedSrcSinkMps.append((extraLB, updSrcMp, updSinkMp, mapping))
            else:
                minRequiredLB = (numLUTRAMUsed / generalSetup.LUTRAMRatioLimit)
                actualRequiredLB = numLBUsed + numLB + numLUTRAMUsed
                requiredLB = max(minRequiredLB, actualRequiredLB)
                availLB = srcMp[LB] 
                requiredBRAM = sinkMp[phyRamType] + numPhyRam
                availBRAM = srcMp[phyRamType]
                if availLB >= requiredLB and availBRAM >= requiredBRAM:
                    canFitCurrentBin = True
                    sinkMp[LB] = (numLBUsed + numLB, numLUTRAMUsed)
                    sinkMp[phyRamType] = requiredBRAM
                    chosenMapping = mapping
                    break
                # Get the updated sinkMp
                updSinkMp = {}
                for srcType in sinkMp:
                    if srcType==LB:
                        updSinkMp[srcType] = (numLBUsed + numLB, numLUTRAMUsed)
                    elif srcType==phyRamType:
                        updSinkMp[srcType] = requiredBRAM
                    else:
                        updSinkMp[srcType] = sinkMp[srcType]
                # Get the updated srcMp 
                # Look at logic blocks first
                updSrcLB = requiredLB
                updSrcMp = {}
                for srcType in srcMp:
                    updSrcMp[srcType] = max(srcMp[srcType], updSrcLB // (generalSetup.ratioMp[srcType] if srcType!=LB else 1))
                # Then look at BRAMs
                updSrcBRAM = requiredBRAM
                updSrcLB = updSrcBRAM * generalSetup.ratioMp[phyRamType]
                for srcType in srcMp:
                    updSrcMp[srcType] = max(updSrcMp[srcType], updSrcLB // (generalSetup.ratioMp[srcType] if srcType!=LB else 1))
                # Calculate number of extra logic blocks needed
                extraLB = updSrcMp[LB] - availLB
                possibleUpdatedSrcSinkMps.append((extraLB, updSrcMp, updSinkMp, mapping))            

        if not canFitCurrentBin:
            # If the current 'bin' can't have the logical ram fit in
            # Iterate through all the possbile mappings again. This time extra physical resources are added
            possibleUpdatedSrcSinkMps = sorted(possibleUpdatedSrcSinkMps, key=lambda x : x[0])
            srcMp = possibleUpdatedSrcSinkMps[0][1]
            sinkMp = possibleUpdatedSrcSinkMps[0][2]
            chosenMapping = possibleUpdatedSrcSinkMps[0][3]
        
        mappings[ramIdx] = (phyID, chosenMapping)
        phyID += 1

    return phyID, mappings

def genFile(mappings, fileName):
    f = open(fileName, 'w')
    for mapping in mappings:
        f.write(mapping+'\n')
    f.close()

def genSolution():
    
    # Initialize the architecture setup
    generalSetup = architecture_T()

    # generate all physical RAMs available
    physicalRams = genPhysicalRams(generalSetup.maxWidthMp)
    # generate all circuits
    circuits = genCircuits('logical_rams.txt', 'logic_block_count.txt');
    
    mappings = []
    phyID = 0
    for circuitID in range(len(circuits)):
        circuit = circuits[circuitID]
        phyID, oneCircuitMappings = genCircuitMapping(generalSetup, circuit, physicalRams, phyID)
        # basic mapping format ...
        for mappingPair in oneCircuitMappings:
            pId = mappingPair[0]
            mapping = mappingPair[1]
            mappings.append(' '.join([
                str(circuitID),
                str(mapping.logicalRam.ramID), 
                str(mapping.numMuxes),
                "LW "+str(mapping.logicalRam.width),
                "LD "+str(mapping.logicalRam.depth),
                "ID "+str(pId),
                "S "+str(mapping.s),
                "P "+str(mapping.p),
                "Type "+ str(generalSetup.typeMp[mapping.phyRam.sizeExp]),
                "Mode "+mapping.logicalRam.mode,
                "W "+str(mapping.phyRam.width),
                "D "+str(mapping.phyRam.depth)
            ]))
    
    genFile(mappings, 'basic.txt')

import time
startTime = time.time()
genSolution()
endTime = time.time()
print('CPU runtime(sec) is: ', endTime-startTime)
