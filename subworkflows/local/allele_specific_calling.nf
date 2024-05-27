//
// Allele specific variant calling
//

include { BCFTOOLS_VIEW                        } from '../../modules/nf-core/bcftools/view/main'
include { BCFTOOLS_INDEX                       } from '../../modules/nf-core/bcftools/index/main'
include { GATK4_ASEREADCOUNTER                 } from '../../modules/nf-core/gatk4/asereadcounter/main'
include { BOOTSTRAPANN                         } from '../../modules/local/bootstrapann'
include { TABIX_BGZIPTABIX                     } from '../../modules/nf-core/tabix/bgziptabix/main'
include { BCFTOOLS_MERGE                       } from '../../modules/nf-core/bcftools/merge/main'
include { RENAME_FILES                         } from '../../modules/local/rename_files'
include { TABIX_TABIX                          } from '../../modules/nf-core/tabix/tabix/main'
include { TABIX_TABIX as TABIX_AFTER_SPLIT     } from '../../modules/nf-core/tabix/tabix/main'
include { TABIX_TABIX as TABIX_REMOVE_DUP      } from '../../modules/nf-core/tabix/tabix/main'
include { TABIX_TABIX as TABIX_ANNOTATE        } from '../../modules/nf-core/tabix/tabix/main'
include { BCFTOOLS_NORM as SPLIT_MULTIALLELICS } from '../../modules/nf-core/bcftools/norm/main'
include { BCFTOOLS_NORM as REMOVE_DUPLICATES   } from '../../modules/nf-core/bcftools/norm/main'
include { ADD_VARCALLER_TO_BED                 } from '../../modules/local/add_varcallername_to_bed'
include { BCFTOOLS_ANNOTATE                    } from '../../modules/nf-core/bcftools/annotate/main'


workflow ALLELE_SPECIFIC_CALLING {
    take:
        ch_ind_vcf_tbi // channel: [mandatory] [ val(meta), [ path(vcf), path(tbi) ] ]
        ch_bam_bai     // channel: [mandatory] [ val(meta), [ path(bam), path(bai) ] ]
        ch_fasta       // channel: [mandatory] [ val(meta), path(fasta) ]
        ch_fai         // channel: [mandatory] [ val(meta), path(fai) ]
        ch_dict        // channel: [mandatory] [ val(meta), path(dict) ]
        ch_intervals   // channel: [mandatory] [ path(intervals) ]
        ch_case_info   // channel: [mandatory] [ val(case_info) ]
        ch_foundin_header  // channel: [mandatory] [ path(header) ]
        variant_caller // parameter: [mandatory] default: 'bcftools'
        ch_genome_chrsizes // channel: [mandatory] [ path(chrsizes) ]

    main:
        ch_versions = Channel.empty()

        // Keep only does variants in the vcf that are SNVs and are heterozygote
        BCFTOOLS_VIEW(
            ch_ind_vcf_tbi,
            [],
            [],
            []
        )

        BCFTOOLS_INDEX(
            BCFTOOLS_VIEW.out.vcf
        )

        ch_vcf_tbi_sample = BCFTOOLS_VIEW.out.vcf.join(BCFTOOLS_INDEX.out.tbi)
        ch_bam_bai_vcf_tbi = ch_bam_bai.join(ch_vcf_tbi_sample)
        GATK4_ASEREADCOUNTER(
            ch_bam_bai_vcf_tbi,
            ch_fasta,
            ch_fai,
            ch_dict,
            ch_intervals
        )

        BOOTSTRAPANN(
            ch_ind_vcf_tbi,
            GATK4_ASEREADCOUNTER.out.csv
        )

        TABIX_BGZIPTABIX(BOOTSTRAPANN.out.vcf)

        TABIX_BGZIPTABIX.out.gz_tbi
                    .collect{it[1]}
                    .ifEmpty([])
                    .toList()
                    .set { file_list_vcf }

        TABIX_BGZIPTABIX.out.gz_tbi
                    .collect{it[2]}
                    .ifEmpty([])
                    .toList()
                    .set { file_list_tbi }

        ch_case_info
            .combine(file_list_vcf)
            .combine(file_list_tbi)
            .set { ch_vcf_tbi }

        ch_vcf_tbi.branch {
            meta, vcf, tbi ->
                single: vcf.size() == 1
                    return [meta, vcf]
                multiple: vcf.size() > 1
                    return [meta, vcf, tbi]
            }.set { ch_case_vcf }

        BCFTOOLS_MERGE( ch_case_vcf.multiple,
            ch_fasta,
            ch_fai,
            []
        )

        RENAME_FILES( ch_case_vcf.single)

        BCFTOOLS_MERGE.out.merged_variants
            .mix( RENAME_FILES.out.output )
            .set { ch_vcf_merged }

        TABIX_TABIX( ch_vcf_merged )

        ch_in_split_multi=ch_vcf_merged.join(TABIX_TABIX.out.tbi)
        SPLIT_MULTIALLELICS(ch_in_split_multi, ch_fasta)
        TABIX_AFTER_SPLIT(SPLIT_MULTIALLELICS.out.vcf)

        ch_remove_dup_in = SPLIT_MULTIALLELICS.out.vcf.join(TABIX_AFTER_SPLIT.out.tbi)
        REMOVE_DUPLICATES(ch_remove_dup_in, ch_fasta)
        TABIX_REMOVE_DUP(REMOVE_DUPLICATES.out.vcf)

        ch_genome_chrsizes.flatten().map{chromsizes ->
            return [[id:variant_caller], chromsizes]
            }
            .set { ch_varcallerinfo }

        ADD_VARCALLER_TO_BED (ch_varcallerinfo).gz_tbi
            .map{meta,bed,tbi -> return [bed, tbi]}
            .set{ch_varcallerbed}

        REMOVE_DUPLICATES.out.vcf
            .join(TABIX_REMOVE_DUP.out.tbi)
            .combine(ch_varcallerbed)
            .combine(ch_foundin_header)
            .set { ch_annotate_in }

        BCFTOOLS_ANNOTATE(ch_annotate_in)

        TABIX_ANNOTATE(BCFTOOLS_ANNOTATE.out.vcf)



        ch_versions = ch_versions.mix(BCFTOOLS_VIEW.out.versions.first())
        ch_versions = ch_versions.mix(BCFTOOLS_INDEX.out.versions.first())
        ch_versions = ch_versions.mix(GATK4_ASEREADCOUNTER.out.versions.first())
        ch_versions = ch_versions.mix(BOOTSTRAPANN.out.versions.first())
        ch_versions = ch_versions.mix(TABIX_BGZIPTABIX.out.versions.first())
        ch_versions = ch_versions.mix( BCFTOOLS_MERGE.out.versions.first() )
        ch_versions = ch_versions.mix( RENAME_FILES.out.versions.first() )
        ch_versions = ch_versions.mix( TABIX_TABIX.out.versions.first() )
        ch_versions = ch_versions.mix( SPLIT_MULTIALLELICS.out.versions.first() )
        ch_versions = ch_versions.mix( TABIX_AFTER_SPLIT.out.versions.first() )
        ch_versions = ch_versions.mix( ADD_VARCALLER_TO_BED.out.versions.first() )
        ch_versions = ch_versions.mix( TABIX_REMOVE_DUP.out.versions.first() )
        ch_versions = ch_versions.mix( BCFTOOLS_ANNOTATE.out.versions.first() )
        ch_versions = ch_versions.mix( TABIX_ANNOTATE.out.versions.first() )

    emit:
        vcf      = BCFTOOLS_ANNOTATE.out.vcf // channel: [ val(meta), [ path(vcf) ] ]
        tbi      = TABIX_ANNOTATE.out.tbi    // channel: [ val(meta), [ path(tbi) ] ]
        versions = ch_versions               // channel: [ path(versions.yml) ]
}
