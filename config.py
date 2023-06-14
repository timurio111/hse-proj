import yaml


with open("config.yaml", "r") as stream:
    try:
        data = yaml.safe_load(stream)
        WIDTH, HEIGHT = map(int, data['APP']['RESOLUTION'].split('*'))
        MAX_FPS = data['APP']['MAX_FPS']
        FULLSCREEN = data['APP']['FULLSCREEN']
        WEBCAM = data['APP']['WEBCAM']
        WEBCAM_SERVER_PORT = data['APP']['WEBCAM_SERVER_PORT']
    except yaml.YAMLError as exc:
        print(exc)

