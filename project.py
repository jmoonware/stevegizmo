import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, State, ctx, dcc
from datetime import datetime as dt
import pytz
import portalocker
import flask
from flask import request, Response
from dash.exceptions import PreventUpdate
import urllib.parse
import logging
from logging import handlers # why?
import settings
import os

# utility functions
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

def send_message_url(message):
	hex_string = message.encode().hex()
	send_url = [settings.rb_send_url,"?"]
	send_url.extend(["imei=",settings.rb_imei,"&"])
	send_url.extend(["username=",settings.rb_username,"&"])
	send_url.extend(["password=",settings.rb_password,"&"])
	send_url.extend(["data=",urllib.parse.quote(hex_string)])
	return("".join(send_url))

def persist_message(message_from, message):
	if message != None:
		try:
			# ISO, timezone-aware UTC time
			isonow = dt.utcnow().astimezone(pytz.UTC).isoformat()
			with portalocker.Lock(settings.message_filename,'a',timeout=5) as mf:
				mf.write("{0}\t{1}\t{2}\n".format(isonow,message_from,message.replace('\t',' ')))
		except Exception as ex:
			logging.getLogger(__name__).error("persist: "+str(ex))
	return

def get_messages():
	lines=[]
	try:
		with portalocker.Lock(settings.message_filename,'r',timeout=5) as mf:
			lines=mf.readlines()
	except Exception as ex:
		logging.getLogger(__name__).error("get_messages: "+str(ex))
	return(lines)

########
# Start of exec
#######

StartDataLogging()

# start last-chance exception block
try:
	server=flask.Flask(__name__)
	app=dash.Dash(__name__,server=server,
		external_stylesheets=[dbc.themes.CYBORG],
		meta_tags=[{'name':'viewport','content':'width=device-width, initial-scale=1'}]
			)

	# Callbacks
	@app.callback(
#		Output("last-sent","children"),
		Input("send-button","n_clicks"),
		State("message-input","value"),
	)
	def on_click(n,message):
		if "send-button" == ctx.triggered_id:
			logging.getLogger(__name__).info("send: " + message)
			logging.getLogger(__name__).debug("send: " + send_message_url(message))
			persist_message("website",message)
		return

	# polling loop to update local message cache
	@app.callback(
		Output("cache-time","children"),
		Output("cache-messages","children"),
		Output("last-sent","children"),
		Input("update-interval","n_intervals"),
		State("cache-time","children"),
		State("cache-messages","children"),
	)
	def on_interval(n_i,cache_time_string,cache_messages_string):
		cache_time = dt.fromisoformat(cache_time_string).timestamp()
		cache_messages = cache_messages_string
		new_time = os.path.getmtime(settings.message_filename)
		if new_time > cache_time: # new messages have been written
			cache_time = new_time
			cache_messages = '\n'.join(get_messages())
		else: # nothing to do
			raise PreventUpdate
		return dt.fromtimestamp(cache_time).isoformat(), cache_messages, cache_messages
	
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
						],id="message-rows"),
					),
				]),
			]),
			html.Div(' ',style={'margin-bottom': 25}),
	        dbc.Card([
				dbc.CardBody([
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
	lo.append(
		dbc.Row(
			dbc.Col(
				dcc.Interval(interval="2000",id="update-interval",n_intervals=0)
			)
		)
	)
	# local storage divs
	lo.append(
		dbc.Row(
			[
				html.Div(id="cache-time",style={'display': 'none'},children=dt.fromtimestamp(os.path.getmtime(settings.message_filename)-1).isoformat()),
				html.Div(id="cache-messages",style={'display': 'none'},children=''),
			]
		)
	)	
	app.layout=html.Div(children=lo)

	# Endpoints
	@server.route('/receive', methods=['GET','POST'])
	def receive_message():
		if 'imei' in request.form:
			logging.getLogger(__name__).debug("receive imei: " + request.form['imei'])
		if 'imei' in request.args:
			logging.getLogger(__name__).debug("receive imei: " + request.args['imei'])
		logging.getLogger(__name__).debug("receive form: " + str(request.form))
		logging.getLogger(__name__).debug("receive args: " + str(request.args))
		return(Response(status=200))
	
except Exception as ex:
	logging.getLogger(__name__).error("Last chance exception:"+str(ex))
	logging.getLogger(__name__).info("Exit on last-chance exception")
finally:
	logging.getLogger(__name__).info("Goodbye")
