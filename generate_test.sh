echo -e "sample_id\tpurpose\tquery_vcf\tquery_vcf_index\ttruth_vcf\ttruth_vcf_index\tbed"
for sample_in in NA12878 NA24694 NA24385
do
    purpose="train"
    query_vcf="inputs/vcfs/$sample_in.chr1.train.vcf.gz"
    query_vcf_index="inputs/vcfs/$sample_in.chr1.train.vcf.gz.csi"
    truth_vcf="inputs/vcfs/$sample_in.truth.vcf.gz"
    truth_vcf_index="inputs/vcfs/$sample_in.truth.vcf.gz.tbi"
    bed="inputs/beds/${sample_in}_train_chr1.bed"
    echo -e $sample_in"\t$purpose\t$query_vcf\t$query_vcf_index\t$truth_vcf\t$truth_vcf_index\t$bed" 
done

for sample_in in NA12878 NA24694 NA24385
do
    purpose="bench"
    query_vcf="inputs/vcfs/${sample_in}.chr2.test.vcf.gz"
    query_vcf_index="inputs/vcfs/${sample_in}.chr2.test.vcf.gz.csi"
    truth_vcf="inputs/vcfs/${sample_in}.truth.vcf.gz"
    truth_vcf_index="inputs/vcfs/${sample_in}.truth.vcf.gz.tbi"
    bed="inputs/beds/${sample_in}_test_chr2.bed"
    echo -e $sample_in"\t$purpose\t$query_vcf\t$query_vcf_index\t$truth_vcf\t$truth_vcf_index\t$bed" 
    
done