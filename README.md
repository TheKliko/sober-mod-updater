# sober-mod-updater
Update your Roblox mods

## Instructions
Before running this program, please make sure that you have all [requirements](#requirements) installed.
1. Download this repository to get the source code
2. Change the [configuration](#configuration) if needed
3. Make sure your mod is [compatible](#mod-compatibility)
4. Run main.py

## Configuration
Default configuration
```json
{
    "target_version": null,
    "mod_path": "~/.var/app/org.vinegarhq.Sober/data/sober/asset_overlay"
}
```

### file_version
Specify the Roblox file version that the mod should be updated for. If the value is missing or `null`, you will be prompted to specify the target version manually. If you don't know which version to use, follow these steps:

1. Open the Roblox app
2. Go to the More tab
3. Choose About, then App information
4. Check for the version number, in this example it is 2.697.926
5. Use the second number, this is your target version, in this example it is 697

<img width="678" height="343" alt="file_version_example" src="https://github.com/user-attachments/assets/47ed9cfe-3d12-4547-b1b2-14d00db04deb" />

### mod_path
Specify the path of the mod that you want to update. If the value is missing or `null`, you will be prompted to specify the path manually. For sober, it should be `~/.var/app/org.vinegarhq.Sober/data/sober/asset_overlay`

## Mod Compatibility

> [!CAUTION]
> You need to know your mods file version **before** your mod breaks, otherwise the updater will move the icons to the wrong positions and break things even more!

To be able to update your mod, it needs to have an info.json file specifying the mods file version:

```json
{
    "fileVersion": 685
}
```
This is the version of Roblox that the mod was made for. If you don't know what this means, go to [Configuration > file_version](#file_version)


## Requirements

| Item | Description|
|---|---|
| [Python](https://www.python.org) | Tested for version 3.14.0, but other versions may work |
| [Requests](https://github.com/psf/requests) | `pip install requests` |
| [Pillow](https://github.com/python-pillow/Pillow)   | `pip install pillow` |
