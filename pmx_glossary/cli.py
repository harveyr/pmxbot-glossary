import click

from pmx_glossary.glossary import Glossary


@click.group()
def cli():
    Glossary.initialize()


@cli.command()
def jsondump():
    """
    Dump all entry data to a json file.
    """
    click.secho('Dumping to json...')
    data, filepath = Glossary.store.dump_to_json()

    print('Dumped {} glossary entries to {}'.format(len(data), filepath))


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def jsonload(path):
    """
    Load entry data from a json file.
    """
    all_entries, inserted = Glossary.store.load_from_json(path)
    all_len, inserted_len = len(all_entries), len(inserted)

    print('Inserted {}/{} entries from file.'.format(all_len, inserted_len))

    if all_len != inserted_len:
        print(
            'This implies that {} entries were already in the database.'.format(
                all_len - inserted_len
            )
        )

    print
