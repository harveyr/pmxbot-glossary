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

    entry_count = len(data['entries'])
    redirect_count = len(data['redirects'])

    print(
        'Dumped {} glossary entries and {} redirects to {}'.format(
            entry_count, redirect_count, filepath
        )
    )


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def jsonload(path):
    """
    Load entry data from a json file.
    """
    all_data, inserted = Glossary.store.load_from_json(path)
    all_entries_count = len(all_data['entries'])
    inserted_entries_count = len(inserted)

    print(
        'Inserted {}/{} entries from file.'.format(
            inserted_entries_count, all_entries_count
        )
    )

    if all_entries_count != inserted_entries_count:
        print(
            'This implies that {} entries were already in the database.'.format(
                all_entries_count - inserted_entries_count
            )
        )

    print


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def load_fixtures(path):
    Glossary.load_fixtures(path)
