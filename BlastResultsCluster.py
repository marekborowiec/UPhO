#!/usr/bin/env python2
# -*- coding: utf-8 -*- 
import argparse
import os
import re
import glob

blast_out_sep = "\t"


def mcl_abc(blastout, expectation, blast_out_sep):
    """Create input file abc for mcl,from a csv blast out and a expectation file """
    outName = 'mcl_%s.abc' % str(expectation)
    myOut = open(outName, 'w')
    in_file = open(blastout, 'r')
    for line in in_file:
        (queryId, subjectId, percIdentity, alnLength, mismatchCount, gapOpenCount, 
         queryStart, queryEnd, subjectStart, subjectEnd, eVal, bitScore) = line.split(blast_out_sep)
        if int(alnLength) >= 50 and float(eVal) <= float(expectation) and float(percIdentity) >= 50.00:
            string ="%s\t%s\t%s\n"%(queryId, subjectId, eVal)
            myOut.write(string)
    in_file.close()
    myOut.close()


def clusters(blastout, expectation, blast_out_sep):
    """This function take two arguments: 1) the blast csv output, and 
    2) an E Value threshold for the formation of clusters. 
    The output is text file with the identifiers of the sequenes clustered on a single line, 
    a hidden parameter in this function is the alignment lenght, Im using 50 but can be  modified."""
    myOut = open("clusters_%s.txt"  % expectation, 'w')
    in_file = open(blastout, 'r')
    previous_query = ''
    Homolog=[]
    for line in in_file:
        (queryId, subjectId, percIdentity, alnLength, mismatchCount, gapOpenCount, 
         queryStart, queryEnd, subjectStart, subjectEnd, eVal, bitScore) = line.split(blast_out_sep)
        current_query = queryId
        if (int(alnLength) >= 100) and float(eVal) <= float(expectation):
            if previous_query != current_query:
                myOut.write(','.join(Homolog) + '\n')
                previous_query = current_query
                Homolog=[]
                Homolog.append(queryId)
                Homolog.append(subjectId)
            else:
                if subjectId not in Homolog:
                    Homolog.append(subjectId)
    myOut.write(','.join(Homolog) + '\n')


def non_redundant(cluster, minTaxa, blast_out_sep):
    """This function filters out clusters with redundant species. 
    Takes as input a cluster file, like the one produces by the fuction clusters, 
    and a minimum number of different species"""
    inFile = open(cluster, 'rw')
    outFile =open("ClustNR_m%d.txt" %minTaxa, "w")
    SetsInspected = []
    for line in inFile:
        SeqIds = line.strip('\n').split(blast_out_sep)
        spp = spp_in_list(SeqIds, sep)
        if len(spp) == len(set(spp)) and len(spp) >= int(minTaxa) and sorted(SeqIds) not in SetsInspected:
            SetsInspected.append(sorted(SeqIds))
            outFile.write(line)
    outFile.close()


def spp_in_list(alist, delim):
    """Return the species from a list of sequece identifiers"""
    spp =[]
    for i in alist:
        spp.append(i.split(delim)[0])
    return spp

                
def redundant(cluster, minTaxa):
    """Produces homolog-groups with at least N different OTUs, 
    allowing redundancy but removing groups including less than a minimum different OTUs """
    inFile = open(cluster, "rw")
    outFile =open("ClustR_m%d.txt" %minTaxa, "w" )
    SetsInspected = []
    for line in inFile:
        SeqIds = (line.strip('\n').split(','))
        spp = spp_in_list(SeqIds,sep)
        nr = set(spp)
        if len(nr) >= int(minTaxa) and SeqIds not in SetsInspected:
            SetsInspected.append(sorted(SeqIds))
            outFile.write(line)
    outFile.close()


#MAIN
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='This script produces clusters of homolog sequences from a csv formatted blast output file.')
    parser.add_argument('-in', 
        dest = 'input', 
        type = str, 
        default= None, 
        help = 'Blast output file to process, if no input is provided the program will try to process a file with extension "csv" in the working diretory.')
    parser.add_argument('-d', 
        dest= 'delimiter', 
        type =str, 
        default= '|', 
        help ='Custom character separating the otu_name from the sequence identifier')
    parser.add_argument('-sc', 
        dest= 'sc',  
        action ='store_true', 
        default= False, help ='When the flag is present only sigle copy clusters, those composed of only one sequences per species , will be written to the output.')
    parser.add_argument('-mcl', 
        dest= 'mcl', 
        action='store_true', 
        default= False, 
        help = "When true, a 'abc' file is produced to use as input for Markov Clustering with Stijn van Dongen's  program mcl.")
    parser.add_argument('-e', 
        dest='expectation', 
        type=float, 
        default = 1e-5, 
        help ='Additional expectation value threshold, default 1e-5.')
    parser.add_argument('-m', 
        dest='minTaxa', 
        type=int, 
        default = 4, 
        help = 'minimum number of different species to keep in each cluster.')
    parser.add_argument('-R', 
        dest='reference', 
        type=str, 
        help= 'Name of the reference file from where to extract individual sequences to form cluster files, if none is provided it is assumed to be a file named "All.fasta" in the working directory')

    args, unknown = parser.parse_known_args()

    sep=args.delimiter

    if args.input == None:
        print 'No BLAST output file was provided'
        csvs=glob.glob("*.csv")
        if len(csvs) > 0:
            csv = csvs[0]
            print 'No BLAST output  provided the file %s in the wd will be tried' % csv
        else:
            print 'Error: A BLAST output file is required to produce clusters. None available!'
    else:
        csv = args.input
    if args.mcl:
        print 'Creating an abc file for mcl'
        mcl_abc(args.input, args.expectation, blast_out_sep)
    else:
        print 'E value filtering and clustering started'
        clusters(csv, args.expectation, blast_out_sep)
        clustFile = 'clusters_%s.txt' %args.expectation
        if not args.sc:
            print 'Minimum taxa filtering started'
            redundant(clustFile, args.minTaxa)
            if args.reference:
                import Get_fasta_from_Ref as GFR
                try:
                    GFR.main("ClustR_m%d.txt" % args.minTaxa, 'clustR_e%s_m%d' % (args.expectation, args.minTaxa), 'bcl', args.reference)
                except:
                    pass
                else:
                    non_redundant(clustFile, args.minTaxa)
                    if args.reference:
                        import Get_fasta_from_Ref as GFR
                        try:
                            GFR.main('ClustNR_m%d.txt' %args.minTaxa,'clustSC_e%s_m%d'  % (args.expectation, args.minTaxa), 'bcl', args.reference)
                        except:
                            pass