# mwman - A package manager for MediaWiki

mwman is a python-based package manager for the MediaWiki wiki software.

It strives to automate the installation of extensions, skins and even MediaWiki itself.

**Warning**: mwman is still in early development and may not be ideal for your production environment needs. Be cautious and have backups!

## Usage

```sh
$ mwman install checkuser $PATH_TO_WIKI # Installs and enables the checkuser extension
$ mwman uninstall checkuser $PATH_TO_WIKI # Removes it again
$ mwman activate/deactivate checkuser $PATH_TO_WIKI # Activate / Deaectivate an extension
$ mwman install-mediawiki master $PATH_TO_WIKI # Installs the master branch of MediaWiki into $PATH_TO_WIKI
```

## Limitations / Issues

- Real support is only provided for the latest master version
- No support for sets of packages
- Many steps of the MediaWiki installation still have to be done manually
- The extension loader is not a proper extension itself
- No search feature
- No support for third-party repositories
- Only supports git for obtaining packages
- No support for different versions of packages
- Very limited metadata information
- No way to view package details

These may change as the project progresses in maturity.

## Disclaimer

This software comes without any warranty.

This software is not associated with the MediaWiki development team nor the Wikimedia Foundation.

## License

mwman is free software and licensed under the terms of the MIT License. See LICENSE.
