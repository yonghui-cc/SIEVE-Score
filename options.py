def Input_func(options,argv):
    for x in [y for y in argv if y[0]=='-']:
        option_name = x[1:]
        options[option_name] = argv[argv.index(x) + 1]

    Check_options(options)
    
    return options

def Check_options(options):
    if options['i'] == None:
        print('No input assigned. quit.')
        quit()

    if options['o'] == None:
        print('No output assigned. quit.')
        quit()

    if options['title'] == None:
        options['title'] = options['i']

    tf = ['show', 'score', 'zeroneg', 'score_correction']
    for x in tf:
        if options[x] in ['False', 'false', 'No', 'no', '0']:
            options[x] = False
        else:
            options[x] = True

    ints = ['cl', 'skip', 'propose']
    for x in ints:
        options[x] = int(options[x])

    floats = ['p', 'm']
    for x in floats:
        options[x] = float(options[x])

    return options
