#!/usr/bin/python
import fileinput
import os
import shutil
import subprocess

from ConfigParser import RawConfigParser as Cfg
from urllib import urlretrieve


def get_plugins(config):
    server = config.get("sources", "server")
    path = config.get("sources", "path")
    sections = config.sections()
    plugins = {}
    for section in sections:
        if section.startswith("plugin:"):
            name = section.partition(":")[2]
            version = config.get(section, "version")
            data = {'name': name, 'version': version}
            data['url'] = server + path % data
            data['filename'] = name + '.hpi'
            plugins[name] = data
    return plugins


def download_plugins(plugins, workarea):
    for plugin, data in plugins.iteritems():
        outpath = os.path.join(workarea, data['filename'])
        print "Retrieving %(name)s from %(url)s..." % data
        urlretrieve(data['url'], outpath)
        print "Done."


def dhmake(buildarea, copyright):
    cmd = ["dh_make", "-n", "-c", copyright, "-s"]
    env = os.environ.copy()
    env["PWD"] = buildarea
    dhm = subprocess.Popen(cmd, cwd=buildarea, env=env)
    dhm.communicate("\n")
    if dhm.returncode:
        raise RuntimeError("dh_make failed", dhm)


def clear_cruft(debarea):
    for fname in os.listdir(debarea):
        if (fname.startswith("README.") or
            fname.endswith(".ex") or
            fname.endswith(".EX")):
            remove = os.path.join(debarea, fname)
            print "Clearing cruft:", remove
            os.remove(remove)


def fix_control(debarea, description):
    for line in fileinput.input(os.path.join(debarea, 'control')):
        if line.startswith("Section:"):
            print "Section: misc"
        elif line.startswith("Homepage:") or line.startswith("#"):
            continue
        elif line.startswith("Description:"):
            print "Description:", description
            print ""
            break
        else:
            print line


def add_inst_files(srcdir, debarea):
    for fname in os.listdir(srcdir):
        fpath = os.path.join(srcdir, fname)
        shutil.copy(fpath, debarea)


def build_binary(buildarea):
    cmd = ["debuild", "-b"]
    subprocess.check_call(cmd, cwd=buildarea)


def build_source(buildarea):
    cmd = ["debuild", "-S", "-sa"]
    subprocess.check_call(cmd, cwd=buildarea)


def dput_source(basedir, changes):
    do_pub = raw_input("Publish [y/n]? ")
    if do_pub.lower() != "y":
        return
    ppa = raw_input("PPA [ppa:kemitche/l2cs-ppa]: ") or "ppa:kemitche/l2cs-ppa"
    cmd = ["dput", ppa, changes]
    subprocess.check_call(cmd, cwd=basedir)


def main():
    assert os.environ['DEBEMAIL']

    config = Cfg()
    config.read("build.cfg")
    basedir = os.getcwd()

    package = config.get("package", "name")
    version = config.get("package", "version")
    copyright = config.get("package", "copyright")
    description = config.get("package", "description")
    changes = "%s_%s.0_source.changes" % (package, version)

    buildarea = os.path.join(basedir, "%s-%s.0" % (package, version))
    debarea = os.path.join(buildarea, "debian")
    workarea = os.path.join(buildarea, package)
    srcdir = os.path.join(basedir, "src")

    print "Building %s (%s) in %s" % (package, version, buildarea)

    plugins = get_plugins(config)

    print "Creating package with plugins:"
    for name in plugins:
        print name

    print ""

    os.makedirs(workarea)

    download_plugins(plugins, workarea)

    dhmake(buildarea, copyright)

    clear_cruft(debarea)

    fix_control(debarea, description)
    add_inst_files(srcdir, debarea)
    
    build_binary(buildarea)
    build_source(buildarea)

    dput_source(basedir, changes)


if __name__ == '__main__':
    main()

