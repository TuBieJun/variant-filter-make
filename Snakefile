SAMPLES = ["NA12878", "NA24694", "NA24385"]

rule all:
    input:
        # expand("results/happy/{sample_id}.summary.csv", sample_id=SAMPLES)
        "results/hap_plot/test_dev.snp.hap.summary.png",
        "results/hap_plot/test_dev.indel.hap.summary.png"


rule extract_features:
    input:
        train_vcf="inputs/vcfs/{sample_id}.chr1.train.vcf.gz",
        train_vcf_index="inputs/vcfs/{sample_id}.chr1.train.vcf.gz.csi",
        train_truth_vcf="inputs/vcfs/{sample_id}.truth.vcf.gz",
        train_truth_vcf_index="inputs/vcfs/{sample_id}.truth.vcf.gz.tbi",
        train_bed="inputs/beds/{sample_id}_train_chr1.bed"
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

rule train_model_snp:
    input:
        features_file=expand("results/features/{samples}_snp_feature_matrix.tsv", samples=SAMPLES),
        train_model_config_file="train_model_config.yaml"
    params:
        info_flags="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR",
        model="mlp"
    output:
        model_file="results/models/test_dev_snp.pkl",
    shell:
        """
        python train_model.py \
              -i {input.features_file} \
              -o {output.model_file} \
              --info-flags {params.info_flags} \
              -c {input.train_model_config_file} \
              --model {params.model}
        """

rule train_model_indel:
    input:
        features_file=expand("results/features/{samples}_indel_feature_matrix.tsv", samples=SAMPLES),
        train_model_config_file="train_model_config.yaml"
    params:
        info_flags="QD,MQ,FS,MQRankSum,ReadPosRankSum,SOR",
        model="mlp"
    output:
        model_file="results/models/test_dev_indel.pkl",
    shell:
        """
        python train_model.py \
              -i {input.features_file} \
              -o {output.model_file} \
              --info-flags {params.info_flags} \
              -c {input.train_model_config_file} \
              --model {params.model}
        """

rule apply_model_snp:
    input:
        model_file="results/models/test_dev_snp.pkl",
        test_vcf="inputs/vcfs/{sample_id}.chr2.test.vcf.gz",
        test_vcf_index="inputs/vcfs/{sample_id}.chr2.test.vcf.gz.csi",
    params:
        batch_size=10000,
        filter_name="ML_SNP_FAIL",
        var_type="snp"
    output:
        "results/apply/{sample_id}.chr2.test.apply.snp.vcf.gz"
    shell:
        """
        python apply_model.py \
            -i {input.test_vcf} \
            -m {input.model_file} \
            -o {output} \
            -t {params.var_type} \
            -f {params.filter_name} \
            -F 
        """

rule apply_model_indel:
    input:
        model_file="results/models/test_dev_indel.pkl",
        test_vcf="inputs/vcfs/{sample_id}.chr2.test.vcf.gz",
        test_vcf_index="inputs/vcfs/{sample_id}.chr2.test.vcf.gz.csi",
    params:
        batch_size=10000,
        filter_name="ML_INDEL_FAIL",
        var_type="indel"
    output:
        "results/apply/{sample_id}.chr2.test.apply.indel.vcf.gz"
    shell:
        """
        python apply_model.py \
            -i {input.test_vcf} \
            -m {input.model_file} \
            -o {output} \
            -t {params.var_type} \
            -f {params.filter_name} \
            -F 
        """

rule merge_snp_indel:
    input:
        snp_vcf="results/apply/{sample_id}.chr2.test.apply.snp.vcf.gz",
        indel_vcf="results/apply/{sample_id}.chr2.test.apply.indel.vcf.gz"
    output:
        vcf="results/apply/{sample_id}.chr2.test.apply.vcf.gz",
        vcf_index="results/apply/{sample_id}.chr2.test.apply.vcf.gz.csi"
    shell:
        """
        bcftools concat -a -O z -W -o {output.vcf} {input.snp_vcf} {input.indel_vcf}
        """

rule hap_py:
    input:
        query_vcf="results/apply/{sample_id}.chr2.test.apply.vcf.gz",
        query_vcf_index="results/apply/{sample_id}.chr2.test.apply.vcf.gz.csi",
        truth_vcf="inputs/vcfs/{sample_id}.truth.vcf.gz",
        truth_vcf_index="inputs/vcfs/{sample_id}.truth.vcf.gz.tbi",
        confident_bed="inputs/beds/{sample_id}_test_chr2.bed",
        ref_fasta="/data/public_db/human_reference/b37/human_g1k_v37.fasta",
        ref_fasta_index="/data/public_db/human_reference/b37/human_g1k_v37.fasta.fai"
    output:
        "results/happy/{sample_id}.summary.csv"
    threads: 8
    shell:
        """
        conda run -n hap.py hap.py --threads {threads} \
            -r {input.ref_fasta} \
            -f {input.confident_bed} \
            -o results/happy/{wildcards.sample_id} \
            {input.truth_vcf} \
            {input.query_vcf}
        """

rule plot_hap:
    input:
        hap_summary_files=expand("results/happy/{sample_id}.summary.csv", sample_id=SAMPLES)
    output:
        "results/hap_plot/test_dev.snp.hap.summary.png",
        "results/hap_plot/test_dev.indel.hap.summary.png"
    params:
        sample_ids=SAMPLES,
        tags = ["mlp", "mlp", "mlp"]
    shell:
        """
        python plot_hap.py -i {input.hap_summary_files} \
              -o results/hap_plot/test_dev.hap.snp.summary.png \
              -s {params.sample_ids} \
              -t {params.tags} \
              --type SNP \
              --filter PASS
        python plot_hap.py -i {input.hap_summary_files} \
              -o results/hap_plot/test_dev.hap.indel.summary.png \
              -s {params.sample_ids} \
              -t {params.tags} \
              --type INDEL \
              --filter PASS
        """