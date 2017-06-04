import os, sys, codecs, ConfigParser, getopt, random, shutil, tarfile, json
from datetime import datetime
import Train


__author__ = "Eugene Su"
__license__ = "Apache License"
__version__ = "2.0"


DEBUG = True
YOLO_ROOT = None
JOB_ROOT = None


def read_global_conf():
    FILE_NAME = 'GlobalConfig.ini'
    SECTION_NAME = 'GLOBAL'
    YOLO_ROOT_OPTION = 'YOLO_ROOT_PATH'
    JOB_ROOT_OPTION = 'JOB_ROOT_PATH'
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.readfp(codecs.open(FILE_NAME, 'r', 'utf-8-sig'))
    global YOLO_ROOT, JOB_ROOT
    if config.has_section(SECTION_NAME):
        if config.has_option(SECTION_NAME, YOLO_ROOT_OPTION):
            YOLO_ROOT = os.path.abspath(config.get(SECTION_NAME, YOLO_ROOT_OPTION))
        else:
            print 'Please set {} in {}'.format(YOLO_ROOT_OPTION, FILE_NAME)
            sys.exit(1)
        if config.has_option(SECTION_NAME, JOB_ROOT_OPTION):
            JOB_ROOT = os.path.abspath(config.get(SECTION_NAME, JOB_ROOT_OPTION))
        else:
            print 'Please set {} in {}'.format(JOB_ROOT_OPTION, FILE_NAME)
            sys.exit(1)
    else:
        print 'Please set {} and {} in {}'.format(YOLO_ROOT_OPTION, JOB_ROOT_OPTION, FILE_NAME)
        sys.exit(1)

    if DEBUG:
        print('{} = {}'.format('YOLO_ROOT', YOLO_ROOT))
        print('{} = {}'.format('JOB_ROOT', JOB_ROOT))

    check_dir(YOLO_ROOT)


def check_dir(path, isCreat=False):
    if DEBUG:
        print 'Checking PATH: {}'.format(path)

    if not os.path.exists(path):
        if isCreat:
            os.makedirs(path)
        else:
            print 'PATH {} does not exist'.format(path)
            sys.exit(1)
    else:
        if not os.path.isdir(path):
            print 'PATH {} is not a folder'.format(path)
            sys.exit(1)


def copy_tree(src, dst, symlinks=False, ignore=None):
    print 'Copying {} to {}'.format(src, dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)
    print 'Copy finished'


def tar_tree(src, dst):
    tar = tarfile.open(dst, 'w')
    tar.add(src, arcname=os.path.basename(src))
    tar.close()


def untar_tree(src, dst):
    tar = tarfile.open(src, 'r')
    tar.extractall(dst)
    tar.close()


def process_cfg(path_dic):
    CFG_FOLDER_NAME = 'cfg'
    TRAIN_DATA_FOLDER_NAME = 'train_data'
    BACKUP_FOLDER_NAME = 'backup'
    path_dic['cfg_folder'] = os.path.join(path_dic['job_folder'], CFG_FOLDER_NAME)
    check_dir(path_dic['cfg_folder'], True)
    path_dic['new_data_cfg_path'] = os.path.join(path_dic['cfg_folder'], os.path.basename(path_dic['data_cfg_path']))
    path_dic['new_net_cfg_path'] = os.path.join(path_dic['cfg_folder'], os.path.basename(path_dic['net_cfg_path']))
    if not os.path.exists(path_dic['new_net_cfg_path']):
        shutil.copy2(path_dic['net_cfg_path'], path_dic['new_net_cfg_path'])

    path_dic['train_data_folder'] = os.path.join(path_dic['job_folder'], TRAIN_DATA_FOLDER_NAME)
    check_dir(path_dic['train_data_folder'], True)
    props = read_yolo_config(path_dic['data_cfg_path'])
    modify_cfg_props(props, 'train', path_dic['data_cfg_path'], path_dic['train_data_folder'])
    modify_cfg_props(props, 'valid', path_dic['data_cfg_path'], path_dic['train_data_folder'])
    modify_cfg_props(props, 'names', path_dic['data_cfg_path'], path_dic['cfg_folder'])
    path_dic['backup_folder'] =os.path.join(path_dic['job_folder'], BACKUP_FOLDER_NAME)
    check_dir(path_dic['backup_folder'], True)
    props['backup'] = path_dic['backup_folder']
    if DEBUG:
        print 'data_cfg_props: {}'.format(props)

    with open(path_dic['new_data_cfg_path'], 'w') as f:
        for key, value in props.items() :
            f.write('{} = {}\n'.format(key, value))
    return props


def read_yolo_config(path, sep_cahr='=', comment_char='#'):
    props = {}
    with open(path, "rt") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith(comment_char):
                key_value = l.split(sep_cahr)
                key = key_value[0].strip()
                value = sep_cahr.join(key_value[1:]).strip().strip('"')
                props[key] = value
    return props


def modify_cfg_props(props, key, cfg_path, copy_dest_folder):
    if props.has_key(key):
        value = props.get(key)
        if not os.path.isabs(value):
            value = os.path.join(YOLO_ROOT, value)
        if not os.path.exists(value):
            print 'The setting of {} [{}]is wrong in {}'.format(key, value, cfg_path)
            sys.exit(1)
        else:
            new_value = os.path.join(copy_dest_folder, os.path.basename(value))
            shutil.copy2(value, new_value)
            props[key] = new_value
    else:
        print 'The setting of {} does exist in {}'.format(key, cfg_path)
        sys.exit(1)


def find_file(path, name):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None


def save_dic(dic, path):
    try:
        with open(path, 'w') as f:
            json.dump(dic, f)
    except (OSError, IOError) as e:
        print e
        sys.exit(1)


def load_dic(path):
    try:
        with open(path, 'r') as f:
            dic = json.load(f)
        return dic
    except (OSError, IOError) as e:
        print e
        sys.exit(1)


def main(argv):
    USAGE_MSG = 'Manager.py -i <id> -c <train/recall/report> -d <training data cfg> -n <network cfg> -w <weight file>'
    SOURCE_FOLDER_NAME = 'yolo'
    CMD_SET = ['train', 'recall', 'report']
    FILE_NAME = 'PathSetting.json'
    cmd = None
    id = None
    path_dic = {'data_cfg_path': None, 'net_cfg_path': None}
    weight_file = None

    read_global_conf()

    try:
        opts, args = getopt.getopt(argv, 'hc:i:d:n:w:', ['cmd=', 'id=', 'data_cfg=', 'net_cfg=', 'weight='])
    except getopt.GetoptError:
        print USAGE_MSG
        sys.exit(2)
    if DEBUG:
        print 'opts: {}' .format(opts)

    for opt, arg in opts:
        if opt == '-h':
            print USAGE_MSG
            sys.exit()
        elif opt in ('-c', '--cmd'):
            cmd = arg
            if not cmd in CMD_SET:
                print USAGE_MSG
                print 'unknown command: {}'.format(cmd)
                sys.exit(1)
        elif opt in ('-i', '--id'):
            id = arg
            check_dir(os.path.join(JOB_ROOT, id))
        elif opt in ('-d', '--data_cfg'):
            if os.path.isabs(arg):
                path_dic['data_cfg_path'] = arg
            else:
                path_dic['data_cfg_path'] = os.path.join(YOLO_ROOT, arg)
        elif opt in ('-n', '--net_cfg'):
            if os.path.isabs(arg):
                path_dic['net_cfg_path'] = arg
            else:
                path_dic['net_cfg_path']= os.path.join(YOLO_ROOT, arg)
        elif opt in ('-w', '--weight'):
            if os.path.isabs(arg):
                weight_file = arg
            else:
                weight_file = os.path.join(YOLO_ROOT, arg)

    if cmd is None:
        print USAGE_MSG
        print 'command is necessary'
        sys.exit(1)

    if id is None:
        if path_dic['data_cfg_path'] is None:
            print USAGE_MSG
            print 'training data cfg is necessary'
            sys.exit(1)

        if path_dic['net_cfg_path'] is None:
            print USAGE_MSG
            print 'network cfg is necessary'
            sys.exit(1)

        if DEBUG:
            print 'training data cfg is {}'.format(path_dic['data_cfg_path'])

        if not os.path.exists(path_dic['data_cfg_path']):
            print 'training data cfg: {} does not exist'.format(path_dic['data_cfg_path'])
            sys.exit(1)

        if DEBUG:
            print 'network cfg is {}'.format(path_dic['net_cfg_path'])

        if not os.path.exists(path_dic['net_cfg_path']):
            print 'network cfg: {} does not exist'.format(path_dic['net_cfg_path'])
            sys.exit(1)

        check_dir(JOB_ROOT, True)
        # generate an unique ID
        id = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1, 1000)).zfill(3)
        if DEBUG:
            print 'ID is {}'.format(id)

        path_dic['job_folder'] = os.path.join(JOB_ROOT, id)
        check_dir(path_dic['job_folder'], True)
        path_dic['yolo_folder'] = os.path.join(path_dic['job_folder'], SOURCE_FOLDER_NAME)
        if not os.path.exists(path_dic['yolo_folder']):
            check_dir(path_dic['yolo_folder'], True)
            # copy yolo source code to job_folder
            copy_tree(YOLO_ROOT, path_dic['yolo_folder'])
            ##tar_tree(YOLO_ROOT, os.path.join(path_dic['yolo_folder'], 'source.tar'))
            ##untar_tree(os.path.join(path_dic['yolo_folder'], 'source.tar'), path_dic['yolo_folder'])

        data_cfg_props = process_cfg(path_dic)

        makefile = find_file(path_dic['yolo_folder'], 'Makefile')
        if  makefile is None:
            print 'Can not find Makefile in {}'.format(path_dic['yolo_folder'])
            sys.exit(1)
        path_dic['makefile_folder'] = os.path.dirname(makefile)
        if DEBUG:
            print 'Makefile is in {}'.format(path_dic['makefile_folder'])

        save_dic(path_dic, os.path.join(path_dic['job_folder'], FILE_NAME))
    else:
        weight_file = None
        path_dic = load_dic(os.path.join(JOB_ROOT, id, FILE_NAME))
        if DEBUG:
            print 'path_dic: {}'.format(path_dic)

        data_cfg_props = read_yolo_config(path_dic['data_cfg_path'])

    if cmd == CMD_SET[0]:
        # train
        Train.process_train(path_dic, weight_file)


if __name__ == "__main__":
   main(sys.argv[1:])