# pmxbot-glossary

Glossary extension for [pmxbot](https://bitbucket.org/yougov/pmxbot/wiki/Home).

## Command Examples

* `!gl define carrot: an orange rod`
    * Creates a definition.
* `!gl define carrot: an orange vegetable`
    * Creates a new definition, but does not overwrite the old one.
* `!gl carrot`
    * Gets the latest definition of carrot.
* `!gl carrot 1`
    * Gets the first definition of carrot.
* `!gl`
    * Gets the latest definition of a random entry.
 
 
## Why?
 
**Hypothesis:** Maintaining definitions of domain lingo via a chat bot is the
best way to keep those definitions up to date and readily accessible
(assuming the group uses some form of internet chat).

This bot is an effort to test that hypothesis. I believe this may be the case
because:

* It allows painless updating and retrieval of the definitions.
* It keeps the definitions in front of the eyes of the domain experts,
  maximizing the chances they will spot an obsolete or misguided entry.