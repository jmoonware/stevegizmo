import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, State, ctx, dcc
from datetime import datetime as dt
import pytz
import portalocker
import flask
from flask import request, Response, make_response
from dash.exceptions import PreventUpdate
import urllib.parse
import logging
from logging import handlers # why?
import live_settings as settings
import os
import requests
import smtplib
from email.message import EmailMessage

# possible return codes for sending message to rockblock device
rb_errs={
	10:"Invalid login credentials",
	11:"No RockBLOCK with this IMEI found on your account",
	12:"RockBLOCK has no line rental",
	13:"Your account has insufficient credit",
	14:"Could not decode hex data",
	15:"Data too long",
	16:"No data",
	99:"System Error",
	}

# provided in call to /receive endpoint 
rb_receive_params = [
		"imei", # ex:"300234010753370",
		"momsn", # ex:"12345",
		"transmit_time", # ex:"12-10-10 10:41:50",
		"iridium_lattitude", # ex:"52.3867",
		"iridium_longitude", # ex:"0.2938",
		"iridium_cep", # ex:"8",
		"data", # ex:"48656c6c6f20576f726c6420526f636b424c4f434b"
]

rb_send_params = [
	"imei",
	"username",
	"password",
	"data",
]

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

def send_message_url(message,url=None):
	hex_string = message.encode().hex()
	if url: # url provided
		send_url = [url,"?"]
	else: # use settings
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

# not tested, needs a separate lock to avoid r/w collisions
def backup_messages():
	if os.path.isfile(settings.message_filename):
		backnum = 0
		while os.path.isfile(settings.message_filename+"."+str(backnum)):
			backnum+=1
		mc = "mv {0} {1}".format(settings.message_filename,settings.message_filename+"."+str(backnum))
		try:
			logging.getLogger(__name__).info('backup_messages: ' + mc)
			ret = os.system(mc)
			logging.getLogger(__name__).info('backup_messages: returned ' + str(ret))
		except Exception as ex:
			logging.getLogger(__name__).error('backup_messages: ' + str(ex))
	return

# this is what should come from Rockblock when a message is sent from the device
def simulate_receive_from_rb(message="test"):
	data = {
		"imei":"300234010753370",
		"momsn":"12345",
		"transmit_time":"12-10-10 10:41:50",
		"iridium_lattitude":"52.3867",
		"iridium_longitude":"0.2938",
		"iridium_cep":"8",
		"data":message.encode().hex()
	}
	test_url="http://rockblock.timeswine.org:5000/receive"

	try:
		result = requests.post(test_url,data=data)
		if result:
			logging.getLogger(__name__).info("simulate: Response Code {0}, Response is: {1} ".format(str(result.status_code),result.text))
		else:
			logging.getLogger(__name__).error("simulate: No response")
	except requests.exceptions.RequestException as rex:
		logging.getLogger(__name__).error("simulate: request exception " + str(rex))

# this posts to an endpoint here to simulate sending to the Rockblock
def simulate_send_to_rb(message):
	test_url = send_message_url(message,settings.rb_test_send_url)
	try:
		result = requests.post(test_url)
		if result:
			logging.getLogger(__name__).info("simulate_send: Response Code {0}, Response is: {1} ".format(str(result.status_code),result.text))
		else:
			logging.getLogger(__name__).error("simulate_send: No response")
	except requests.exceptions.RequestException as rex:
		logging.getLogger(__name__).error("simulate_send: request exception " + str(rex))
	return

# this notifies email users each time the /receive endpoint is called correctly
def notify_users(message):
	try:
		server = smtplib.SMTP(settings.smtp_server,settings.smtp_server_port)
		server.starttls()
		server.login(settings.smtp_account,settings.smtp_password)
		for dest in settings.smtp_destinations:
			msg = EmailMessage()
			msg['Subject']='Notification from Rockblock'
			msg['From']='coms@mail.timeswine.org'
			msg['To']=dest
			msg.set_content(message)
			res = server.send_message(msg)
			logging.getLogger(__name__).info("Notify: "+ dest + ": "+ str(res))
		server.quit()

	except Exception as ex:
		logging.getLogger(__name__).error("Notify: " + str(ex))

	return

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
	app.title = 'SandsComStat'

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
			try:
				ret = requests.post(send_message_url(message))
				logging.getLogger(__name__).info("send: response {0}, {1}".format(str(ret),ret.text))
			except requests.exceptions.RequestException as rex:
				logging.getLogger(__name__).error("send: {0}".format(str(rex)))
		return

	# polling loop to update local message cache
	@app.callback(
		Output("cache-time","children"),
		Output("cache-messages","children"),
		Output("message-rows","children"),
		Input("update-interval","n_intervals"),
		State("cache-time","children"),
		State("cache-messages","children"),
	)
	def on_interval(n_i,cache_time_string,cache_messages_string):
		cache_time = dt.fromisoformat(cache_time_string).timestamp()
		cache_messages = cache_messages_string
		out_rows = []
		new_time = 0
		if os.path.isfile(settings.message_filename):
			new_time = os.path.getmtime(settings.message_filename)
		if new_time != cache_time: # new messages have been written
			cache_time = new_time
			msg_lines = get_messages()
			try:
				msg_elements = [x.split('\t') for x in msg_lines]
				msg_fmt_dt = [(x[0].split('T')[0],x[0].split('T')[-1].split('.')[0]) for x in msg_elements]
				cache_messages = '\n'.join(msg_lines)
				out_rows = [html.Tr([html.Td(x[0]),html.Td(x[1]),html.Td(y[1]),html.Td(y[2])]) for x,y in zip(msg_fmt_dt,msg_elements)] 
			except IndexError as ie:
				logging.getLogger(__name__).error("on_interval: {1}".format(str(ie)))
				backup_messages() # corrupt message somewhere...
		else: # nothing to do
			raise PreventUpdate
		return dt.fromtimestamp(cache_time).isoformat(), cache_messages, out_rows

	@app.callback(
		Output("collapse", "is_open"),
		Input("collapse-button", "n_clicks"),
		State("collapse", "is_open"),
	)
	def toggle_collapse(n, is_open):
		if n:
			return not is_open
		return is_open

	@app.callback(
		Output("textarea-logs", "value"),
		Input("load-logs-button", "n_clicks"),
	)
	def get_logs(n):
		lines=[]
		if n:
			with open(settings.log_filename,'r') as f:
				lines = f.readlines()
		return ''.join(lines) 


	# Layout
	lo=[html.H1('Sands Com Station',style={'textAlign': 'center'})]
	lo.append(html.Div(' ',style={'margin-bottom': 25}))
	lo.append(
		dbc.Row([
	        dbc.Card([
				dbc.CardBody([
					html.H3("Messages",className="text-primary"),
					dbc.Table([
						html.Thead(html.Tr([html.Th("UTC Date",style={'width':'10%'}), html.Th("UTC Time",style={'width':'10%'}),html.Th("From",style={'width':'10%'}),html.Th("Message"), ])),
						html.Tbody([
#						html.Tr([
#							html.Td(html.H4("...",id="last-sent")),
#							]),
						],id="message-rows"),
					]),
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
	# advanced drop-down, usually initially hidden
	# a little white space
	lo.append(
		dbc.Row(
			dbc.Col(
				html.Div(' ',style={'margin-bottom': 25})
			)
		)
	)

	# the button to open the collapsed area
	lo.append(
		dbc.Row([
			dbc.Col(
				dbc.Button(
					"Advanced",
					id="collapse-button",
					n_clicks=0,
					color='secondary',
				),
				width = 'auto'
			),
		],
		justify='center')
	)
	# a little white space
	lo.append(
		dbc.Row(
			dbc.Col(
				html.Div(' ',style={'margin-bottom': 25})
			)
		)
	)

	# the collapsed area
	lo.append(
		dbc.Row([
			dbc.Collapse([
				dbc.Card(
					dbc.CardBody([
						dbc.Table(
							html.Tbody([
								html.Tr([
									html.Td(
										dbc.Button(
											"Logs",
											id="load-logs-button",
											n_clicks=0,
											color='secondary',
										),
									)]
								),
								html.Tr([
									html.Td(
										dcc.Textarea(
											id='textarea-logs',
											value='Log data goes here...',
											style={'width':'100%','height':300},
										),
									)]
								),
							])
						)
					]), # cardbody
				), # Card
			],
			id="collapse",
			is_open=False,
			)
		]) # Row
	) # append



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
				html.Div(id="cache-time",style={'display': 'none'},children=dt.fromtimestamp(0).isoformat()),
				html.Div(id="cache-messages",style={'display': 'none'},children=''),
			]
		)
	)	
	app.layout=html.Div(children=lo)

	# Endpoints
	@server.route('/receive', methods=['POST'])
	def receive_message():
		try:
			logging.getLogger(__name__).debug("receive {0} {1} {2}".format(str(request),str(request.form),str(request.args)))
			for field in rb_receive_params:
				if field in request.form:
					logging.getLogger(__name__).debug("receive {0}: {1}".format(field,request.form[field]))
				else:
					logging.getLogger(__name__).error("receive {0}: Missing".format(field))
#		logging.getLogger(__name__).debug("receive form: " + str(request.form))
		except Exception as ex:
			logging.getLogger(__name__).error("receive: " + str(ex))
		return(Response(status=200))

	# call this route instead of the live Rockblock url to test logic
	@server.route('/test_url',methods=['POST'])
	def test_send():
		ret = make_response("OK, 12345",200)
		ret.mimetype = "text/plain"
		# log the fields provided
		try:
			for field in rb_send_params:
				if field in request.form:
					logging.getLogger(__name__).debug("test_send {0}: {1}".format(field,request.form[field]))
				else:
					logging.getLogger(__name__).error("test_send {0}: Missing".format(field))
		except Exception as ex:
			logging.getLogger(__name__).error("test_send: " + str(ex))
		return(ret)

except Exception as ex:
	logging.getLogger(__name__).error("Last chance exception:"+str(ex))
	logging.getLogger(__name__).info("Exit on last-chance exception")
finally:
	logging.getLogger(__name__).info("Reached finally OK")
