#!/usr/bin/env python3
# mwman - Package manager for MediaWiki
'''MWMan - A package manager for MediaWiki'''

import sys
import subprocess
import shutil
import os
import stat
import configparser

import requests
import yaml
import fire
import colorama

MEDIAWIKI_REPO_URL = 'https://github.com/wikimedia/mediawiki.git'
PACKAGE_REPO_URL = 'https://github.com/spycrab/mwman-packages.git'

def get_data_dir():
    '''Get the location where the package data is stored'''
    return os.path.dirname(os.path.realpath(__file__))

def get_pkg_dir():
    '''Get the root of the package repository'''
    path = os.path.join(os.path.expanduser('~'), '.mwman', 'packages')

    if not os.path.isdir(path):
        MWMan().update_repository()

    return path

def run_command(args, working_dir='.'):
    '''Execute a command'''
    return subprocess.call(args, shell=(os.name == 'nt'), cwd=working_dir)

def fatal_error(msg):
    '''Print an error and return'''
    print(colorama.Style.BRIGHT + 'FATAL: '+ colorama.Fore.RED + colorama.Style.NORMAL +"%s" % msg)
    sys.exit(1)

def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)

def rmtree_force(path):
    '''Remove all files recursively even when read-only'''
    shutil.rmtree(path, onerror=remove_readonly)

def check_mediawiki_install(path):
    '''Checks whether a given path points to a MediaWiki installation or not'''
    is_install = os.path.isdir(os.path.join(path, 'extensions')) and os.path.isdir(os.path.join(path, 'skins'))

    if not is_install:
        fatal_error("'%s' is not a valid MediaWiki installation" % os.path.abspath(path))

def check_for_command(cmd):
    '''Checks whether or not the execution of a command raises errors'''
    print("Checking for %s..." % cmd)
    ret = subprocess.call([cmd, '-v'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    if ret != 0:
        print("%s not found." % cmd)
        return False
    return True

def composer(path, fatal=True):
    '''Run composer'''
    ret = run_command(['composer', 'update', '--no-dev'], path)

    if fatal and ret != 0:
        fatal_error('Failed to run composer')

    return ret == 0

def do_maintenance(destination, script, params=None):
    '''Execute a MediaWiki maintenance script'''
    if params is None:
        params = []

    ret = run_command(['php', os.path.join(destination, 'maintenance', "%s.php" % script)] + params)

    if ret != 0:
        fatal_error("Failed to run maintenance script %s." % script)

def find_package(name):
    '''Get package by name'''
    for pkg_type in ['skin', 'extension']:
        path = os.path.join(get_pkg_dir(), "%ss" % pkg_type, "%s.yml" % name)

        if not os.path.isfile(path):
            continue

        stream = open(path, 'r')
        package = yaml.load(stream)

        return package

    return None

def toggle_package(packages, activate, destination):
    '''Activates or deactivates a given listen of packages'''
    check_mediawiki_install(destination)

    verb = 'activated' if activate else 'deactivated'

    if isinstance(packages, str):
        packages = [packages]

    for pkg in packages:

        package = find_package(pkg)

        if package is None:
            fatal_error("No such package %s." % pkg)

        pkg_type = package['type']

        config = configparser.ConfigParser()

        config.read(os.path.join(destination, 'MWMan.ini'))

        if not config.has_section("%ss" % pkg_type):
            fatal_error('No such section.')

        pkg_status = config["%ss" % pkg_type].get(package['name'], None)

        if pkg_status is None:
            fatal_error("Package %s not present" % pkg)

        if pkg_status == ('1' if activate else '0'):
            print(colorama.Style.BRIGHT + "Package %s already %s." % (pkg, verb))
            continue

        config["%ss" % pkg_type][package['name']] = '1' if activate else '0'

        with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
            config.write(configfile)

        print(colorama.Fore.GREEN + "%s %s." % (pkg, verb))

class MWMan():
    '''A package manager for MediaWiki'''
    @staticmethod
    def check_sanity():
        '''Check whether or not all required tools are installed'''
        if not check_for_command('npm'):
            fatal_error('Please install npm.')

        if not check_for_command('php'):
            fatal_error('Please install php.')

        if not check_for_command('composer'):
            fatal_error('Please install composer.')

        print('All OK.')

    @staticmethod
    def activate(packages, destination):
        '''Activate a package'''
        toggle_package(packages, True, destination)

    @staticmethod
    def deactivate(packages, destination):
        '''Deactivate a package'''
        toggle_package(packages, False, destination)

    @staticmethod
    def auto_add(destination):
        '''Enable mwman for a repository'''
        check_mediawiki_install(destination)

        local_settings_path = os.path.join(destination, 'LocalSettings.php')
        include_line = "include('MWMan.php');"

        if not os.path.isfile(local_settings_path):
            print('No LocalSettings.php! Have you completed the installation yet?')
            exit(1)

        sure = input("Are you sure you want to append %r to your LocalSettings.php [y/N]? " % include_line)

        if sure != 'y':
            print('Aborting...')
            exit(1)

        local_settings = open(local_settings_path, 'a')

        local_settings.write("\n\n#Added by mwman\n%s\n" % include_line)

    @staticmethod
    def maintenance(destination, script, params=None):
        '''Run a maintenance script'''
        if isinstance(params, str):
            params = [params]

        do_maintenance(destination, script, params)

    @staticmethod
    def uninstall(packages, destination):
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

            if package is None:
                fatal_error("No such package %s" % pkg)

            pkg_type = package['type']

            install_path = os.path.join(destination, "%ss" % pkg_type, package['name'])

            if not os.path.isdir(install_path):
                fatal_error("Package %s is not installed!" % pkg)

            rmtree_force(install_path)

            config = configparser.ConfigParser()

            config.read(os.path.join(destination, 'MWMan.ini'))

            config["%ss" % pkg_type].pop(pkg, None)

            with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
                config.write(configfile)

            print(colorama.Fore.GREEN + "Removed %s successfully." % pkg)
            break

    @staticmethod
    def install_mediawiki(version, destination):
        '''Install MediaWiki'''
        ret = run_command(['git', 'clone', '-b', version,
                           '--single-branch', '--depth', '1', MEDIAWIKI_REPO_URL, destination])

        if ret != 0:
            fatal_error("Failed to clone repository")

        composer(destination)

        print('Installing MWMan.php...')

        shutil.copyfile(os.path.join(get_data_dir(), 'MWMan.php'),
                        os.path.join(destination, 'MWMan.php'))

        config = configparser.ConfigParser()

        config['extensions'] = {}
        config['skins'] = {}

        with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
            config.write(configfile)

        print(colorama.Fore.GREEN + 'Done! Visit the wiki from your browser to configure it.')
        print('Note: This is a barebones installation. You might want to install some packages before using it.')
        print('Please run auto-add after the installation is complete for mwman to function properly.')

    @staticmethod
    def install(packages, destination='.'):
        '''Install a package'''
        check_mediawiki_install(destination)

        if isinstance(packages, str):
            packages = [packages]

        for pkg in packages:
            package = find_package(pkg)

            if package is None:
                fatal_error("No such package %s." % pkg)

            pkg_type = package['type']

            install_path = os.path.join(destination, "%ss" % pkg_type, package['name'])

            if os.path.isdir(install_path):
                print("Package %s already installed" % pkg)
                return

            print("==> Installing %s by %s" % (package['name'], ', '.join(package['authors'])))


            # Install dependencies

            dependencies = package.get('depends', None)

            if dependencies is not None:
                for dependency in dependencies:
                    install(dependency, destination)

            # Source

            source = package['source']['type']

            if source == 'git':
                print("Cloning git repository from %s..." % package['source']['url'])
                ret = run_command(['git', 'clone', '-b', package['source']['branch'],
                                   '--single-branch', '--depth', '1',
                                   package['source']['url'], install_path])

                if ret != 0:
                    fatal_error('Failed to clone repository')
            else:
                fatal_error("Unknown source '%s'" % source)

            # Enable installed

            config = configparser.ConfigParser()

            config.read(os.path.join(destination, 'MWMan.ini'))

            if not config.has_section("%ss" % pkg_type):
                config.add_section("%ss" % pkg_type)

            config["%ss" % pkg_type][package['name']] = '1'

            with open(os.path.join(destination, 'MWMan.ini'), 'w') as configfile:
                config.write(configfile)

            # Install

            install = package.get('install', None)

            if install is not None:
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

    @staticmethod
    def update_repository():
        '''Update the mwman package repository'''
        path = os.path.join(os.path.expanduser('~'), '.mwman', 'packages')

        os.makedirs(path, exist_ok=True)

        if not os.path.isdir(os.path.join(get_pkg_dir(), '.git')):
            print('No package repository present, cloning now...')

            run_command(['git', 'clone', PACKAGE_REPO_URL, '.'], path)
        else:
            print('Updating repository...')
            run_command(['git', 'pull'], get_pkg_dir())

def main():
    '''Entry point for this script'''
    colorama.init(autoreset=True)
    fire.Fire(MWMan)

if __name__ == '__main__':
    main()
