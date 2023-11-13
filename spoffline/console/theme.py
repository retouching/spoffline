from rich.theme import Theme


class SpofflineTheme(Theme):
    def __init__(self):
        super().__init__({
            # Define colors
            'green': '#1DB954',
            'white': '#ecf0f1',
            'red': '#c0392b',

            # define rules
            'rule.text': 'green',
            'rule.line': 'white',
            'danger': 'bold red',
            'info': 'bold green',
            'warn': 'bold #d35400',
            'bar.complete': 'green',
            'bar.pulse': 'green',
            'bar.finished': 'green',
            'progress.percentage': 'bold green',
            'progress.remaining': 'bold green',
            'progress.description': 'white'
        }, inherit=True)
