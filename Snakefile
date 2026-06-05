SAMPLES = ["NA12878", "NA24694", "NA24385"]

rule extract_features:
    input:
        train_vcf="/data/users/liteng/my_dev/product/wegene_basic_data_bench/data/NA12878304_T7_phase1_8G/NA12878304_T7_phase1_8G.vcf.gz",
        train_vcf_index="/data/users/liteng/my_dev/product/wegene_basic_data_bench/data/NA12878304_T7_phase1_8G/NA12878304_T7_phase1_8G.vcf.gz.tbi",
        train_truth_vcf="/data/public_db/giab/GRCH37/latest/NA12878_benchmark.vcf.gz",
        train_truth_vcf_index="/data/public_db/giab/GRCH37/latest/NA12878_benchmark.vcf.gz.tbi",
        train_bed="/data/users/liteng/my_dev/product/wegene_basic_data_bench/beds/itech_mt_NA12878_highconf_v4.2.1.bed"
    output:
        snp_matrix="results/features/{sample_id}_snp_feature_matrix.tsv",
        indel_matrix="results/features/{sample_id}_indel_feature_matrix.tsv"
    params:
        prefix="results/features/{sample_id}",
        vcf_filter_flag=".,PASS,MLrejected",
        info_flag_snp="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR",
        info_flag_indel="QD,FS,MQRankSum,ReadPosRankSum,SOR"
    shell:
        """
        python extract_features.py {input.train_vcf} \
            {input.train_truth_vcf} \
            {input.train_bed} \
            {params.prefix} \
            --sample-id {wildcards.sample_id} \
            --vcf-filter-flag "{params.vcf_filter_flag}" \
            --info-flags-snp "{params.info_flag_snp}" \
            --info-flags-indel "{params.info_flag_indel}"
        """

# rule train_model:
#     input:
#         matrix=expand("results/features/{sample_id}_snp_feature_matrix.tsv", sample_id=SAMPLES),
#         # indel_matrix=expand("results/features/{sample_id}_indel_feature_matrix.tsv", sample_id=SAMPLES)
#     output:
#         model="results/models/{sample_id}_model.pkl"
#     params:
#         model_name="mlp"
#     shell:
#         """
#         python train_model.py {input.snp_matrix} {input.indel_matrix} {output.model} --model-name {params.model_name}
#         """