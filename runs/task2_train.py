if __name__ == '__main__':
    from datasets.ISIC2018.data_generators import Task2DataGenerator
    from misc_utils.print_utils import Tee, log_variable
    from misc_utils.filename_utils import get_log_filename
    from misc_utils.filename_utils import get_weights_filename
    from misc_utils.filename_utils import get_csv_filename

    from misc_utils.model_utils import get_model_metrics
    from misc_utils.model_utils import get_model_loss

    from misc_utils.visualization_utils import BatchVisualization

    from keras.callbacks import ReduceLROnPlateau, ModelCheckpoint, CSVLogger
    from keras.optimizers import Adam
    from keras.initializers import RandomNormal
    from models import backbone
    import sys

    input_shape = (1024, 1024, 3)
    num_classes = 1
    backbone_name = 'unet'
    k_fold = 0
    version = '0'
    model_name = 'task2_%s' % backbone_name
    run_name = 'task2_%s_k%d_v%s' % (backbone_name, k_fold, version)
    from_run_name = None

    logfile = open(get_log_filename(run_name=run_name), 'w+')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, logfile)

    # Network architecture
    upsampling_type = 'deconv'
    bottleneck = False
    batch_normalization = False
    init_nb_filters = 16
    growth_rate = 2
    nb_blocks = 7
    nb_layers_per_block = 2
    max_nb_filters = 512

    encoder_activation = 'relu'
    decoder_activation = 'relu'
    use_activation = True
    use_soft_mask = False
    prior_probability = 0.01
    kernel_initializer = RandomNormal(mean=0.0, stddev=0.01)

    if backbone_name == 'unet': # no pretrained network
        backbone_options = dict(
            nb_blocks=nb_blocks,
            init_nb_filters=init_nb_filters,
            growth_rate=growth_rate,
            nb_layers_per_block=nb_layers_per_block,
            max_nb_filters=max_nb_filters,
            activation=encoder_activation,
            batch_normalization=batch_normalization,
        )
    else:
        backbone_options = dict()

    # training parameter
    batch_size = 1
    initial_epoch = 0
    epochs = 50
    init_lr = 1e-4  # Note learning rate is very important to get this to train stably
    min_lr = 1e-10
    reduce_lr = 0.5
    patience = 2
    loss = 'fl'
    alpha = 0.25
    gamma = 2
    metrics = ['jaccard_index', 'pixelwise_sensitivity', 'pixelwise_specificity']

    # data augmentation parameters
    horizontal_flip = True
    vertical_flip = True
    rotation_angle = 45.
    width_shift_range = 0.1
    height_shift_range = 0.1
    data_gen_args = dict(horizontal_flip=horizontal_flip,
                         vertical_flip=vertical_flip,
                         rotation_range=rotation_angle,
                         width_shift_range=width_shift_range,
                         height_shift_range=height_shift_range)

    data_gen = Task2DataGenerator(attribute_names=['pigment_network', ], **data_gen_args)

    debug = False
    print_model_summary = True
    plot_model_summary = True

    if from_run_name:
        model = backbone(backbone_name).segmentation_model(load_from=from_run_name)
    else:
        model = backbone(backbone_name, **backbone_options).segmentation_model(input_shape=input_shape,
                                                                               num_classes=1,
                                                                               upsampling_type=upsampling_type,
                                                                               bottleneck=bottleneck,
                                                                               init_nb_filters=init_nb_filters,
                                                                               growth_rate=growth_rate,
                                                                               nb_layers_per_block=nb_layers_per_block,
                                                                               max_nb_filters=max_nb_filters,
                                                                               activation=decoder_activation,
                                                                               use_activation=use_activation,
                                                                               kernel_initializer=kernel_initializer,
                                                                               prior_probability=prior_probability,
                                                                               save_to=run_name,
                                                                               print_model_summary=print_model_summary,
                                                                               plot_model_summary=plot_model_summary,
                                                                               name=model_name)

    loss = get_model_loss(loss, num_classes, alpha=alpha, gamma=gamma)
    metrics = get_model_metrics(metrics, num_classes)
    model.compile(optimizer=Adam(lr=init_lr), loss=loss, metrics=metrics)

    log_variable(var_name='input_shape', var_value=input_shape)
    log_variable(var_name='num_classes', var_value=num_classes)
    log_variable(var_name='upsampling_type', var_value=upsampling_type)
    log_variable(var_name='bottleneck', var_value=bottleneck)
    log_variable(var_name='init_nb_filters', var_value=init_nb_filters)
    log_variable(var_name='growth_rate', var_value=growth_rate)
    log_variable(var_name='nb_layers_per_block', var_value=nb_layers_per_block)
    log_variable(var_name='max_nb_filters', var_value=max_nb_filters)
    log_variable(var_name='encoder_activation', var_value=encoder_activation)
    log_variable(var_name='decoder_activation', var_value=decoder_activation)
    log_variable(var_name='batch_normalization', var_value=batch_normalization)
    log_variable(var_name='use_activation', var_value=use_activation)
    log_variable(var_name='use_soft_mask', var_value=use_soft_mask)

    log_variable(var_name='batch_size', var_value=batch_size)
    log_variable(var_name='initial_epoch', var_value=initial_epoch)
    log_variable(var_name='epochs', var_value=epochs)
    log_variable(var_name='init_lr', var_value=init_lr)
    log_variable(var_name='min_lr', var_value=min_lr)
    log_variable(var_name='patience', var_value=patience)

    log_variable(var_name='horizontal_flip', var_value=horizontal_flip)
    log_variable(var_name='vertical_flip', var_value=vertical_flip)
    log_variable(var_name='width_shift_range', var_value=width_shift_range)
    log_variable(var_name='height_shift_range', var_value=height_shift_range)
    log_variable(var_name='rotation_angle', var_value=rotation_angle)

    log_variable(var_name='n_samples_train', var_value=data_gen.num_training_samples)
    log_variable(var_name='n_samples_valid', var_value=data_gen.num_validation_samples)

    sys.stdout.flush()  # need to make sure everything gets written to file

    callbacks = [
        ReduceLROnPlateau(monitor='val_loss',
                          factor=reduce_lr,
                          patience=patience,
                          verbose=1,
                          mode='auto',
                          min_lr=min_lr),
        ModelCheckpoint(get_weights_filename(run_name),
                        monitor='val_loss',
                        save_best_only=True,
                        save_weights_only=True,
                        verbose=True),
        CSVLogger(filename=get_csv_filename(run_name))
    ]

    model.fit_generator(generator=data_gen.flow(subset='training',
                                                batch_size=batch_size),
                        steps_per_epoch=data_gen.num_training_samples // batch_size,
                        epochs=epochs,
                        initial_epoch=initial_epoch,
                        verbose=1,
                        validation_data=data_gen.flow(subset='validation',
                                                      batch_size=batch_size),
                        validation_steps=data_gen.num_validation_samples // batch_size,
                        callbacks=callbacks,
                        workers=8,
                        use_multiprocessing=False)

    sys.stdout = original