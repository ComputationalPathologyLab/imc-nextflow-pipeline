nextflow.enable.dsl=2

params.input            = "data/Tiffs"
params.outdir           = "results"
params.python           = "python"
params.steinbock_image  = "ghcr.io/bodenmillergroup/steinbock:0.16.1"

process VALIDATE_ROI_CHANNELS {
    tag "validate_channels"

    publishDir "${params.outdir}/validation", mode: 'copy'

    input:
    path roi_dirs

    output:
    path "channel_check.json"

    script:
    def roi_args = roi_dirs.collect { "\"${it}\"" }.join(' ')
    """
    ${params.python} ${projectDir}/bin/validate_roi_channels.py channel_check.json ${roi_args}
    """
}

process MAKE_SHARED_PANEL {
    tag "panel"

    publishDir "${params.outdir}/panel", mode: 'copy'

    input:
    path roi_dir

    output:
    path "panel.csv"

    script:
    """
    ${params.python} ${projectDir}/bin/make_shared_panel.py "${roi_dir}" panel.csv
    """
}

process STACK_ROI {
    tag "${roi_dir.baseName}"

    publishDir "${params.outdir}/stacked", mode: 'copy'

    input:
    path roi_dir

    output:
    path "${roi_dir.baseName}.tiff"

    script:
    """
    ${params.python} ${projectDir}/bin/stack_one_roi.py "${roi_dir}" "${roi_dir.baseName}.tiff"
    """
}

process MAKE_IMAGES_CSV {
    tag "images_csv"

    publishDir "${params.outdir}", mode: 'copy'

    input:
    path stacked_tiffs

    output:
    path "images.csv"

    script:
    def tiff_args = stacked_tiffs.collect { "\"${it}\"" }.join(' ')
    """
    mkdir -p stacked
    cp ${tiff_args} stacked/
    ${params.python} ${projectDir}/bin/make_images_csv.py stacked images.csv
    """
}

process STEINBOCK_SEGMENT {
    tag "segment"

    publishDir "${params.outdir}/steinbock", mode: 'copy'

    container "${params.steinbock_image}"

    input:
    path stacked_tiffs
    path panel_csv
    path images_csv

    output:
    path "project/masks", emit: masks

    script:
    def tiff_args = stacked_tiffs.collect { "\"${it}\"" }.join(' ')
    """
    mkdir -p project/img

    cp ${tiff_args} project/img/
    cp "${panel_csv}" project/panel.csv
    cp "${images_csv}" project/images.csv

    cd project
    steinbock segment deepcell --app mesmer --minmax
    """
}

process STEINBOCK_MEASURE_INTENSITIES {
    tag "measure_intensities"

    publishDir "${params.outdir}/steinbock", mode: 'copy'

    container "${params.steinbock_image}"

    input:
    path stacked_tiffs
    path panel_csv
    path images_csv
    path masks_dir

    output:
    path "project/intensities", emit: intensities

    script:
    def tiff_args = stacked_tiffs.collect { "\"${it}\"" }.join(' ')
    """
    mkdir -p project/img

    cp ${tiff_args} project/img/
    cp "${panel_csv}" project/panel.csv
    cp "${images_csv}" project/images.csv
    cp -r "${masks_dir}" project/masks

    cd project
    steinbock measure intensities
    """
}

workflow {
    roi_dirs = Channel
        .fromPath("${params.input}/*", type: 'dir', checkIfExists: true)
        .ifEmpty { error "No ROI directories found under: ${params.input}" }
        .toSortedList { a, b -> a.name <=> b.name }

    first_roi = Channel
        .fromPath("${params.input}/*", type: 'dir', checkIfExists: true)
        .filter { it.isDirectory() }
        .first()

    roi_dirs_for_stack = Channel
        .fromPath("${params.input}/*", type: 'dir', checkIfExists: true)
        .filter { it.isDirectory() }

    validated = VALIDATE_ROI_CHANNELS(roi_dirs)
    panel_ch  = MAKE_SHARED_PANEL(first_roi)
    stack_ch  = STACK_ROI(roi_dirs_for_stack)
    images_ch = MAKE_IMAGES_CSV(stack_ch.collect())
    masks_ch  = STEINBOCK_SEGMENT(
        stack_ch.collect(),
        panel_ch,
        images_ch
    )

    STEINBOCK_MEASURE_INTENSITIES(
        stack_ch.collect(),
        panel_ch,
        images_ch,
        masks_ch.masks
    )
}