#!/usr/bin/env python
# coding: utf-8

# In[9]:


import logging
import requests
import os
import boto3
import json
from io import StringIO
import io
from csv import reader
import numpy as np
import pandas as pd
from flask import Flask, redirect, url_for, request, render_template
from flask_googlecharts import LineChart
from flask_googlecharts import GoogleCharts
from pandas.core.common import flatten
import time
import http.client
from concurrent.futures import ThreadPoolExecutor
import json

app = Flask(__name__)
AWSAccessKeyId= 'AKIA4W34AHIX3LSRFU6E'
AWSSecretKey='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'

#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 1

def doRender(tname,values={}):
    if not os.path.isfile(os.path.join(os.getcwd(),'templates/'+tname)):
        return render_template('index.html')
    return render_template(tname,**values)

#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 3

@app.route('/parlambda',methods=['POST'])
def parlambda():
    import http.client
    if request.method=='POST':
        lampar = request.form.get('resources')
        lampar = int(lampar)
        runs=[value for value in range(lampar)]
        shots=request.form.get('shots')
        minhistory=request.form.get('minhistory')
        Signal=str(request.form.get('Signal'))
        
        #starting the time
        counttime = time.time()
        
#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 3

    def getpage(id):
        try:
            host = "ew2wc8mlfl.execute-api.us-east-1.amazonaws.com" #aws lambda link 
            c = http.client.HTTPSConnection(host)
            json= '{ "minhistory": ' + str(minhistory) + ',"shots": ' + str(shots) + ', "Signal":' + '"' + Signal + '"' + '}'
            c.request("POST", "/default/lam_par", json)  #name of the lambda function
            response = c.getresponse()
            data = response.read().decode('utf-8')
            #print(data)
            #print( data, " from Thread", id )
        except IOError:
            print( 'Failed to open ', host )
            
            
#importing json to read data using json.loads() method
        import json
        json_data = json.loads(data)
        return json_data
    
#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 3
#parallel_implementation
    def getpages():
        with ThreadPoolExecutor() as executor:
            results=executor.map(getpage, runs)
        return results

    get_results = getpages()
    final_data = []
    value_95=[]
    value_99=[]
    mean_95=[]
    mean_99=[]
    cost_list = []
    
    for k in get_results:
        final_data.append(k)
    print(final_data)

    for j in final_data:
        v95 = j.get("v95")
        value_95.append(v95)
        value_95=list(flatten(value_95))
        
        v99 = j.get("v99")
        value_99.append(v99)
        value_99=list(flatten(value_99))
        
        m95 = j.get("mean95")
        mean_95.append(m95)
        mean_95=list(flatten(mean_95))
        
        m99 = j.get("mean99")
        mean_99.append(m99)
        mean_99=list(flatten(mean_99))
        
        
    mean_v_95 = np.mean(mean_95)
    mean_v_99 = np.mean(mean_99)
    
    #caluculating the cost
    #Referred from https://aws.amazon.com/lambda/pricing/
    
    costforGBsec = 0.0000000500
    final_time = (time.time() - counttime)
    finalcost = (final_time*costforGBsec)
    
    for k in range(lampar):
        cost_list.append(finalcost)
    #print(cost_list)
    avgcost = np.mean(cost_list)
    
#plotting the chart referred from https://pythonhosted.org/Flask-GoogleCharts/

    len_risk_chart = list(range(len(value_95)))
    charts = GoogleCharts(app)
    risk_row=[[len_risk_chart[l],value_95[l],value_99[l],mean_v_95,mean_v_99] for l in range(len(len_risk_chart))]
    risk_chart = LineChart("risk_chart", options={'title': 'Trading chart for BP.L',"width": 700, "height": 500})
    risk_chart.add_column("string", "Today's date")
    risk_chart.add_column("number", "Value of 95")
    risk_chart.add_column("number", "Value of  99")
    risk_chart.add_column("number", "Mean value of 95")
    risk_chart.add_column("number", "Mean value of 99")
    risk_chart.add_rows(risk_row)
    charts.register(risk_chart)    
    
    #results tables
    tabledata = {"Resources":runs, "Value of 95":mean_95,"Value of 99":mean_99, "Cost":cost_list}
    result_table=pd.DataFrame(data=tabledata)
    result_table.set_index(['Resources'])
    
    #mean result table
    meantabledata = {"Average value of 95": [mean_v_95], "Average value of 99": [mean_v_99], "Average cost": [avgcost]}
    meantabledata_table = pd.DataFrame(data= meantabledata)
    meantabledata_table.set_index(['Average value of 95'])

    def s3listbuckets():
        tabledata1 = {"Resources":runs,'Shots':shots, 'minium history':minhistory, "Signal":Signal, "R95":mean_95,"R99":mean_99, "Cost":cost_list}
        #print('run', runs)
        print(cost_list)
#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 4
        os.environ['AWS_SHARED_CREDENTIALS_FILE']='./cred' #reading the file
        s3 = boto3.resource('s3')
        s3buk= s3.Object('adutest','historypage.csv')
        dataread = s3buk.get()['Body'].read().decode('UTF-8')
        
        bucket = 'adutest'  # already created on S3
        csv_buffer = StringIO()
        df=pd.DataFrame(tabledata1)
        df.to_csv(csv_buffer,index=False, mode='a', header=False)   
        s3.Object(bucket, 'historypage.csv').put(Body=dataread+csv_buffer.getvalue())  #writing the file
    
    s3listbuckets()   
    
    return doRender('signalgraph.html',{'meantabledata_table':meantabledata_table.to_html(header='true'),'result_table':result_table.to_html(header='true')})
    
#code Referred from Cloud Computing course materials by Dr. Lee Gillam lab 4

@app.route('/viewbucket',methods=['POST'])

def viewbucket():    
    import http.client
    if request.method=='POST':
        os.environ['AWS_SHARED_CREDENTIALS_FILE']='./cred' #reading the file
        s3 = boto3.resource('s3')
        s3buk= s3.Object('adutest','historypage.csv')
        dataread = s3buk.get()['Body'].read().decode('UTF-8')
        csv_buffer = io.StringIO(dataread)
        df2=pd.read_csv(csv_buffer)
        df3 = df2.to_html(header='true')    
        
    return doRender('audit.html',{'history':df2.to_html(header='true')})  


#code Referred from Cloud Computing course materials by Dr. Lee Gillam

# code Referred from https://boto3.amazonaws.com/v1/documentation/api/latest/guide/migrationec2.html#launching-new-instances
@app.route('/EC2instance',methods=['POST'])
def EC2instance():
    import http.client
    if request.method=='POST':
        resources = request.form.get('resources')
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        ec2 = boto3.resource('ec2', aws_access_key_id=AWSAccessKeyId, aws_secret_access_key=AWSSecretKey)
        ec2.create_instances(ImageId='ami-0dc48d699c665dae5', MinCount=1, MaxCount=resources)
    return doRender('index.html')

# code Referred from https://boto3.amazonaws.com/v1/documentation/api/latest/guide/migrationec2.html#launching-new-instances        
@app.route('/instancestop', methods=['POST'])        
def instancestop():
    import http.client
    if request.method=='POST':
        resources = request.form.get('resources')
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        ec2 = boto3.resource('ec2', aws_access_key_id=AWSAccessKeyId, aws_secret_access_key=AWSSecretKey)
        ids=[]
        instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for instance in instances:
            #print(instance.id, instance.instance_type)
            ids.append(instance.id)
        #print(ids)
        ec2.instances.filter(InstanceIds=ids).stop()
        ec2.instances.filter(InstanceIds=ids).terminate()
    return doRender('terminate.html')

@app.route('/',defaults={'path':''})

@app.route('/<path:path>')


def mainPage(path):
    return doRender(path)

@app.errorhandler(500)

def server_error(e):
    logging.exception('ERROR!')
    return """
    An error occured: <pre>{}</pre>
    """.format(e),500

if __name__ == '__main__':
    app.run()    
    main()
    

