<?php
# MWMan Extension Loader

# Protect against web entry
if (!defined('MEDIAWIKI')) {
	exit;
}

$ini = parse_ini_file('MWMan.ini', TRUE);

if (array_key_exists('extensions', $ini))
{
   foreach ($ini['extensions'] as $extension => $value)
   {
       if ($value)
           wfLoadExtension($extension);
   }
}
if (array_key_exists('skins', $ini))
{
   foreach ($ini['skins'] as $skin => $value)
   {
    if ($value)
        wfLoadSkin($skin);
   }
}
