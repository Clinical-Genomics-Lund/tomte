//
// Allignment
//

include { CAT_FASTQ            } from '../../modules/nf-core/cat/fastq/main'
include { FASTP                } from '../../modules/nf-core/fastp/main'
include { STAR_ALIGN           } from '../../modules/nf-core/star/align/main'
include { SAMTOOLS_INDEX } from '../../modules/nf-core/samtools/index/main'
include { RNA_DOWNSAMPLE       } from '../../modules/local/rna_downsample'
include { RNA_SUBSAMPLE_REGION } from '../../modules/local/rna_subsample_region.nf'

workflow ALIGNMENT {
    take:
        reads
        star_index
        gtf
        platform
        subsample_bed
        seed_frac
        num_reads
        subsample_region_switch
        downsample_switch

    main:
        ch_versions = Channel.empty()

        CAT_FASTQ(reads)
        ch_versions = ch_versions.mix(CAT_FASTQ.out.versions.first())

        FASTP(CAT_FASTQ.out.reads,[],false,false)
        ch_versions = ch_versions.mix(FASTP.out.versions.first())

        STAR_ALIGN(FASTP.out.reads, star_index, gtf, false, 'illumina', false)
        ch_versions = ch_versions.mix(STAR_ALIGN.out.versions.first())

        SAMTOOLS_INDEX( STAR_ALIGN.out.bam )
        ch_versions = ch_versions.mix(SAMTOOLS_INDEX.out.versions.first())

        ch_bam_bai = Channel.empty()
        ch_bam_bai_out = Channel.empty()

        if (subsample_region_switch) {
            RNA_SUBSAMPLE_REGION( STAR_ALIGN.out.bam, subsample_bed, seed_frac)
            ch_versions = ch_versions.mix(RNA_SUBSAMPLE_REGION.out.versions.first())
            ch_bam_bai = ch_bam_bai.mix(RNA_SUBSAMPLE_REGION.out.bam_bai)
            if (!downsample_switch) {
                ch_bam_bai_out = ch_bam_bai.mix(RNA_SUBSAMPLE_REGION.out.bam_bai)
            }
        } else {
            ch_bam_bai = ch_bam_bai.mix(STAR_ALIGN.out.bam.join(SAMTOOLS_INDEX.out.bai))
             if (!downsample_switch) {
                ch_bam_bai_out = STAR_ALIGN.out.bam.join(SAMTOOLS_INDEX.out.bai)
            }
        }

        if (downsample_switch) {
            RNA_DOWNSAMPLE( ch_bam_bai, num_reads)
            ch_versions = ch_versions.mix(RNA_DOWNSAMPLE.out.versions.first())
            ch_bam_bai_out = ch_bam_bai.mix(RNA_DOWNSAMPLE.out.bam_bai)
        }

    emit:
        merged_reads   = CAT_FASTQ.out.reads
        fastp_report   = FASTP.out.json
        bam            = STAR_ALIGN.out.bam
        bam_bai        = STAR_ALIGN.out.bam.join(SAMTOOLS_INDEX.out.bai)
        bam_ds_bai     = ch_bam_bai_out
        gene_counts    = STAR_ALIGN.out.tab
        star_log_final = STAR_ALIGN.out.log_final
        star_wig       = STAR_ALIGN.out.wig_mult_str1
        versions       = ch_versions
}
