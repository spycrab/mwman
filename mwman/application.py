#!/usr/bin/env python3
# mwman - Package manager for MediaWiki

import sys
import subprocess
import shutil
import os, stat
import configparser

import requests
import yaml
import fire
import colorama

MEDIAWIKI_REPO_URL = 'https://github.com/wikimedia/mediawiki.git'
PACKAGE_REPO_URL = 'https://github.com/spycrab/mwman-packages.git'

def get_data_dir():
    return os.path.dirname(os.path.realpath(__file__))

def get_pkg_dir():
    path = os.path.join(os.path.expanduser('~'), '.mwman', 'packages')

    if not os.path.isdir(path):
        MWMan().update_repository()

    return path

def run_command(args, working_dir='.'):
    return subprocess.call(args, shell=(os.name == 'nt'), cwd=working_dir)

def fatal_error(s):
    print(colorama.Style.BRIGHT + 'FATAL: '+ colorama.Fore.RED + colorama.Style.NORMAL +"%s" % s)
    sys.exit(1)

def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)

def rmtree_force(path):
    shutil.rmtree(path, onerror=remove_readonly)

def check_mediawiki_install(path):
    is_install = os.path.isdir(os.path.join(path, 'extensions')) and os.path.isdir(os.path.join(path, 'skins'))

    if not is_install:
        fatal_error("'%s' is not a valid MediaWiki installation" % os.path.abspath(path))

def check_for_command(c):
    print("Checking for %s..." % c)
    if subprocess.call([c, '-v'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True) != 0:
        print("%s not found." % c)
        return False
    return True

def composer(path, fatal=True):
    ret = run_command(['composer', 'update', '--no-dev'], path)

    if not fatal:
        return ret == 0

    if ret != 0:
        fatal_error('Failed to run composer')

def do_maintenance(destination, script, params=[]):
    ret = run_command(['php', os.path.join(destination, 'maintenance', "%s.php" % script)] + params)

    if ret != 0:
        fatal_error("Failed to run maintenance script %s." % script)
    
def find_package(name):
    for type in ['skin', 'extension']:
        path = os.path.join(get_pkg_dir(), "%ss" % type, "%s.yml" % name)

        if not os.path.isfile(path):
            continue

        stream = open(path, 'r')
        package = yaml.load(stream)

        return package

    return None

def toggle_package(packages, activate, destination):
    check_mediawiki_install(destination)

    verb = 'activated' if activate else 'deactivated'

    if isinstance(packages, str):
        packages = [packages]

    for pkg in packages:

        package = find_package(pkg)

        if package == None:
            fatal_error("No such package %s." % pkg)

        type = package['type']
        
        config = configparser.ConfigParser()

        config.read(os.path.join(destination, 'MWMan.ini'))

        if not config.has_section("%ss" % type):
            fatal_error('No such section.')

        pkg_status = config["%ss" % type].get(package['name'], None)

        if pkg_status == None:
            fatal_error("Package %s not present" % pkg)

        if pkg_status == ('1' if activate else '0'):
            print(colorama.Style.BRIGHT + "Package %s already %s." % (pkg, verb))
            continue

        config["%ss" % type][package['name']] = '1' if activate else '0'

        with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
            config.write(configfile)

        print(colorama.Fore.GREEN + "%s %s." % (pkg, verb))

class MWMan(object):
    '''A package manager for MediaWiki'''
    def check_sanity(self):
        if not check_for_command('npm'):
            fatal_error('Please install npm.')

        if not check_for_command('php'):
            fatal_error('Please install php.')

        if not check_for_command('composer'):
            fatal_error('Please install composer.')

        print('All OK.')

    def activate(self, packages, destination):
        '''Activate a package'''
        toggle_package(packages, True, destination)

    def deactivate(self, packages, destination):
        '''Deactivate a package'''
        toggle_package(packages, False, destination)

    def auto_add(self, destination):
        '''Enable mwman for a repository'''
        check_mediawiki_install(destination)

        local_settings_path = os.path.join(destination, 'LocalSettings.php')
        include_line =  "include('MWMan.php');"
        
        if not os.path.isfile(local_settings_path):
            print('No LocalSettings.php! Have you completed the installation yet?')
            exit(1)        
        
        sure = input("Are you sure you want to append %r to your LocalSettings.php [y/N]? " % include_line)

        if sure != 'y':
            print('Aborting...')
            exit(1)

        local_settings = open(local_settings_path, 'a')
        
        local_settings.write("\n\n#Added by mwman\n%s\n" % include_line)
        
    def maintenance(self, destination, script, params=[]):
        '''Run a maintenance script'''
        if isinstance(params, str):
            params = [params]
            
        do_maintenance(destination, script, params)
        
    def uninstall(self, packages, destination):
        '''Uninstall a package'''
        check_mediawiki_install(destination)

        if isinstance(packages, str):
            packages = [packages]

        sure = input("Are you sure you want to remove %s [y/N]? " % ','.join(packages))

        if sure != 'y':
            print('Aborting...')
            exit(1)

        for pkg in packages:

            package = find_package(pkg)

            if package == None:
                fatal_error("No such package %s" % pkg)

            type = package['type']

            install_path = os.path.join(destination, "%ss" % type, package['name'])

            if not os.path.isdir(install_path):
                fatal_error("Package %s is not installed!" % pkg)

            rmtree_force(install_path)

            config = configparser.ConfigParser()

            config.read(os.path.join(destination, 'MWMan.ini'))

            config["%ss" % type].pop(pkg, None)

            with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
                config.write(configfile)

            print(colorama.Fore.GREEN + "Removed %s successfully." % pkg)
            found = True
            break

    def install_mediawiki(self, version, destination):
        '''Install MediaWiki'''
        ret = run_command(['git', 'clone', '-b', version,
                           '--single-branch', '--depth', '1', MEDIAWIKI_REPO_URL, destination])

        if ret != 0:
            fatal_error("Failed to clone repository")

        composer(destination)

        print('Installing MWMan.php...')

        shutil.copyfile(os.path.join(get_data_dir(), 'MWMan.php'), os.path.join(destination, 'MWMan.php'))

        config = configparser.ConfigParser()

        config['extensions'] = {}
        config['skins'] = {}

        with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
            config.write(configfile)

        print(colorama.Fore.GREEN + 'Done! Visit the wiki from your browser to configure it.')
        print('Note: This is a barebones installation. You might want to install some skins and/or extensions before using it.')
        print('Please run auto-add after the installation is complete for mwman to function properly.')

    def install(self, packages, destination='.'):
       '''Install a package'''
       check_mediawiki_install(destination)

       if isinstance(packages, str):
           packages = [packages]

       for pkg in packages:

           package = find_package(pkg)

           if package == None:
               fatal_error("No such package %s." % pkg)

           type = package['type']

           install_path = os.path.join(destination, "%ss" % type, package['name'])

           if os.path.isdir(install_path):
               print("Package %s already installed" % pkg)
               return

           print("==> Installing %s by %s" % (package['name'], ', '.join(package['authors'])))


           # Install dependencies

           dependencies = package.get('depends', None)

           if dependencies != None:
               for dependency in dependencies:
                   self.install(dependency, destination)

           # Source

           source = package['source']['type']

           if source == 'git':
               print("Cloning git repository from %s..." % package['source']['url'])
               ret = run_command(['git', 'clone', '-b', package['source']['branch'],
                                   '--single-branch', '--depth', '1', package['source']['url'], install_path])

               if ret != 0:
                   fatal_error('Failed to clone repository')
           else:
               fatal_error("Unknown source '%s'" % source)

           # Enable installed

           config = configparser.ConfigParser()

           config.read(os.path.join(destination, 'MWMan.ini'))

           if not config.has_section("%ss" % type):
               config.add_section("%ss" % type)

           config["%ss" % type][package['name']] = '1'

           with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
               config.write(configfile)

           # Install

           install = package.get('install', None)

           if install != None:
               if install.get('update', False):
                   print('Updating MediaWiki...')
                   do_maintenance(destination, 'update', ['--quick'])

               if install.get('composer', False):
                   print('Running composer...')

                   if not composer(install_path, False):
                       rmtree_force(install_path)
                       fatal_error('Failed to run composer')

               if install.get('script', False):
                   print('Running install script...')
                   ret = subprocess.Popen('\n'.join(install['script']), shell=True, cwd=install_path)

                   if ret != 0:
                       rmtree_force(install_path)
                       fatal_error('Failed to run install script')

           print(colorama.Fore.GREEN + "%s installed successfully." % pkg)

    def update_repository(self):
        '''Update the mwman package repository'''
        path = os.path.join(os.path.expanduser('~'), '.mwman', 'packages')

        os.makedirs(path, exist_ok = True)

        if not os.path.isdir(os.path.join(get_pkg_dir(), '.git')):
            print('No package repository present, cloning now...')

            run_command(['git', 'clone', PACKAGE_REPO_URL, '.'], path)
        else:
            print('Updating repository...')
            run_command(['git', 'pull'], get_pkg_dir())

def main():
    colorama.init(autoreset=True)
    fire.Fire(MWMan)
            
if __name__ == '__main__':
    main()
