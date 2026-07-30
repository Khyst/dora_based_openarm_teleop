# Verify the image download

The SHA-256 hash for hamsa_v2.zip is the following: 

`52d98766b5f340f5df3e77287b2a825d278c62318d5b3a5b8bf4af2e67063752`

Verify that one of the following commands gives you the same hash.

## Linux

`sha256sum /path/to/image`

## MacOS

`shasum -a 512 /path/to/image`

## Windows

`certUtil -hashfile C:\path\to\image SHA256`
