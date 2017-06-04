import os, sys, shutil


__author__ = "Eugene Su"
__license__ = "Apache License"
__version__ = "2.0"


def process_train(path_dic, weight_file = None):
    CMD_FILE_NAME = 'train.run'
    if not weight_file is None:
        if not os.path.exists(weight_file):
            print 'weight file: {} does not exist'.format(weight_file)
            sys.exit(1)
        else:
            orgi_weight_file = weight_file
            weight_file = os.path.join(path_dic['cfg_folder'], os.path.basename(orgi_weight_file))
            if not weight_file is orgi_weight_file:
                shutil.copy2(orgi_weight_file, weight_file)
    else:
        list = os.listdir(path_dic['backup_folder'])
        files = [x for x in list if os.path.isfile(os.path.join(path_dic['backup_folder'], x))]
        if len(files) > 0:
            weight_file = os.path.join(path_dic['backup_folder'], files[-1])
            print 'weight file is {}'.format(weight_file)

    train_cmd = os.path.join(path_dic['makefile_folder'], 'darknet') + ' detector train '
    train_cmd = train_cmd + path_dic['new_data_cfg_path'] + ' ' + path_dic['new_net_cfg_path']
    if not weight_file is None:
        train_cmd = train_cmd + ' ' + weight_file
    print train_cmd

    cmd_file = os.path.join(path_dic['job_folder'], CMD_FILE_NAME)
    try:
        with open(cmd_file, 'w') as f:
            f.write(train_cmd)
    except (OSError, IOError) as e:
        print e
        sys.exit(1)

    os.system(train_cmd)

