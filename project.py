import dash
import dash_bootstrap_components as dbc
from dash import html,Input,Output,ctx
from datetime import datetime as dt
import flask
import logging
from logging import handlers # why?
import settings

def StartDataLogging():
	logFormatString='\t'.join(['%(asctime)s','%(levelname)s','%(message)s'])
	level=logging.DEBUG
	maxbytes=10000000
	rfh=handlers.RotatingFileHandler(filename=settings.log_filename,maxBytes=maxbytes,backupCount=10)
	sh=logging.StreamHandler()
	logging.basicConfig(format=logFormatString,handlers=[sh,rfh],level=level)
	logging.captureWarnings(True)
	logger=logging.getLogger(__name__)
	logger.critical("Logging Started, level={0}".format(level))


StartDataLogging()

# start last-chance exception block
try:
	server=flask.Flask(__name__)
	app=dash.Dash(__name__,server=server,
		external_stylesheets=[dbc.themes.CYBORG],
		meta_tags=[{'name':'viewport','content':'width=device-width, initial-scale=1'}]
			)
	
	# Layout
	lo=[html.H1('Sands Com Station',style={'textAlign': 'center'})]
	lo.append(html.Div(' ',style={'margin-bottom': 25}))
	lo.append(
		dbc.Row([
	        dbc.Card([
				dbc.CardBody([
					html.H3("Messages",className="text-primary"),
					dbc.Table(html.Tbody([
						html.Tr([
							html.Td(html.H4("...",id="last-sent")),
							]),
						]),
					),
				]),
			]),
			html.Div(' ',style={'margin-bottom': 25}),
	        dbc.Card([
				dbc.CardBody([
					html.H3("Send Message",className="text-primary"),
					dbc.Table(html.Tbody([
						html.Tr([
							html.Td(dbc.Input(id="message-input",placeholder="Type a message...",size="md",type="text")),
							]),
						html.Tr([
							html.Td(dbc.Button("Send",id="send-button",color="primary")),
							]),
						]),
					),
				]),
			]),
		])
	)
	
	app.layout=html.Div(children=lo)
	
	# Callbacks
	@app.callback(
		Output("last-sent","children"),
		Input("send-button","n_clicks"),
		Input("message-input","value")
	)
	def on_click(n,message):
		if "send-button" == ctx.triggered_id:
			logging.getLogger(__name__).info("send: " + message)
			return(message)


	# Endpoints
	
except Exception as ex:
	logging.getLogger(__name__).error("Last chance exception:"+str(ex))
	logging.getLogger(__name__).info("Exit on last-chance exception")
finally:
	logging.getLogger(__name__).info("Goodbye")
