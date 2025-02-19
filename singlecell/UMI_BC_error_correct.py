
import os, sys
from csv import DictReader, DictWriter
from collections import Counter, defaultdict
from Bio.Seq import Seq

def edit_distance(seq1, seq2):
    assert len(seq1)==len(seq2)
    diff = 0
    for i in range(len(seq1)):
        diff += seq1[i]!=seq2[i]
    return diff

def error_correct_BC_or_UMI(records, key, threshold=1):
    """
    :param records: should be list of records all from the same gene!
    """
    assert key in ('BC', 'UMI')
    merge_map = {}
    bc_count = Counter()
    for r in records: bc_count[r[key]] += 1

    # most common BC, in decreasing order
    bc_sorted = [bc for bc,count in bc_count.most_common()]

    i = 0
    while i < len(bc_sorted)-1:
        j = i + 1
        while j < len(bc_sorted):
            if edit_distance(bc_sorted[i], bc_sorted[j]) <= threshold:
                #merge j into i
                merge_map[bc_sorted[j]] = bc_sorted[i]
                bc_sorted.pop(j)
            else:
                j += 1
        i += 1

    #if len(merge_map) > 0:
    #    print merge_map
     ##   raw_input()
    return merge_map


def main(csv_filename, output_filename, shortread_bc={}, only_top_ranked=False):

    recs_by_gene = defaultdict(lambda: [])
    reader = DictReader(open(csv_filename), delimiter='\t')

    FIELDS = reader.fieldnames + ['BC_ed', 'UMI_ed', 'BC_match', 'BC_top_rank']
    f = open(output_filename, 'w')
    writer = DictWriter(f, FIELDS, delimiter='\t')
    writer.writeheader()

    for r in reader:
        recs_by_gene[r['gene']].append(r)

    # error correct BCs by gene group
    for gene in recs_by_gene:
        recs_by_bc = defaultdict(lambda: [])
        bc_merge_map = error_correct_BC_or_UMI(recs_by_gene[gene], 'BC')
        for r in recs_by_gene[gene]:
            if r['BC'] in bc_merge_map:
                r['BC_ed'] = bc_merge_map[r['BC']]
            else:
                r['BC_ed'] = r['BC']
            recs_by_bc[r['BC']].append(r)
        # now error correct by UMI
        for bc in recs_by_bc:
            umi_merge_map = error_correct_BC_or_UMI(recs_by_bc[bc], 'UMI')
            for r in recs_by_bc[bc]:
                if r['UMI'] in umi_merge_map:
                    r['UMI_ed'] = umi_merge_map[r['UMI']]
                else:
                    r['UMI_ed'] = r['UMI']

                BC_ed_rev = str(Seq(r['BC_ed']).reverse_complement())

                r['BC_match'] = 'Y' if BC_ed_rev in shortread_bc else 'N'
                r['BC_top_rank'] = 'Y' if (r['BC_match']=='Y' and shortread_bc[BC_ed_rev]=='Y') else 'N'

                if (not only_top_ranked or r['BC_top_rank']=='Y'):
                    writer.writerow(r)


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("input_csv", help="Input CSV")
    parser.add_argument("output_csv", help="Output CSV")
    parser.add_argument("--bc_rank_file", help="(Optional) cell barcode rank file from short read data")
    parser.add_argument("--only_top_ranked", action="store_true", default=False, help="(Optional) only output those that are top-ranked. Must have --bc_rank_file.")

    args = parser.parse_args()

    shortread_bc = {}  # dict of cell barcode -> "Y" for top ranked
    if args.bc_rank_file is not None:
        reader = DictReader(open(args.bc_rank_file), delimiter='\t')
        for r in reader:
            shortread_bc[r['cell_barcode']] = r['top_ranked']
    else:
        if args.only_top_ranked:
            print("--bc_rank_file must be given if using --only_top_ranked!", file=sys.stderr)
            sys.exit(-1)

    main(args.input_csv, args.output_csv, shortread_bc, args.only_top_ranked)