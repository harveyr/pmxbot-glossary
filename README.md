# pmxbot-glossary

Glossary extension for [pmxbot](https://bitbucket.org/yougov/pmxbot/wiki/Home).

[![Build Status](https://travis-ci.org/harveyr/pmxbot-glossary.svg?branch=master)](https://travis-ci.org/harveyr/pmxbot-glossary)

## Command Examples

* `!whatis define carrot: An orange rod`
    * Creates a definition.
* `!whatis define carrot: An orange vegetable. For more, see http://en.wikipedia.org/wiki/Carrot`
    * Creates a new definition, but does not overwrite the old one.
* `!whatis carrot`
    * Gets the latest definition of carrot.
* `!whatis carrot 1`
    * Gets the first definition of carrot.
* `!whatis`
    * Gets the latest definition of a random entry.
 
 
## Why?

This extension is an effort to test the following hypothesis:

Maintaining definitions of domain lingo via a chat bot is the
best way to keep those definitions up to date and readily accessible
(assuming the group uses some form of internet chat).

I believe this may be the case because:

* It allows painless updating of the definitions (no pull requests, etc.).
* It allows painless retrieval of the definitions.
* It enables somewhat automatic review of definitions as they are added
  or retrieved.
* It creates "accidental" education: you'll learn stuff just sitting in a
  channel and watching the definitions scroll by.
* Along those lines, it keeps the definitions in front of the eyes of the
  domain experts, maximizing the chances they will spot an obsolete,
  misguided, or missing entry.
