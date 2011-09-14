from plog import app

if __name__ == '__main__':
    try:
        server_name = app.config.get('SERVER_NAME')
        port = int(server_name.split(':')[-1])
    except:
        port = 8080
    app.run(port=port)

