import unittest
from conversation import respond

class Tokenizer:
    def apply_chat_template(self,messages,**kwargs):
        self.messages=messages
        return '\n'.join(row['content'] for row in messages)
    def encode(self,prompt,**kwargs):return prompt.split()
class Engine:
    def __init__(self,text='Hello! How can I help?'):self.tokenizer=Tokenizer();self.text=text
    def generate(self,prompt,tokens=48,clean=False,on_text=None):
        self.prompt=prompt;self.clean=clean
        if on_text:on_text(self.text)
        return {'text':self.text,'seconds':.01,'output_tokens':7}
def outcome():
    return {'input':'hi','account':{'orders':[{'id':'NL-1042','total':849000,'refunded':0,'payment_method':'Visa ending 4242'}],'cases':[]},
            'request':{'status':'answered','reason':'No state-changing action requested','order_id':None,'amount':0},
            'reply':'Your message was received.'}
class ConversationTests(unittest.TestCase):
    def test_clean_native_response_and_actual_history(self):
        engine=Engine();chunks=[]
        value=respond(engine,outcome(),[{'role':'user','content':'My headphones crackle.'},{'role':'assistant','content':'Does it happen on another device?'}],chunks.append)
        self.assertTrue(engine.clean)
        self.assertEqual(value['history_messages'],2)
        self.assertIn('My headphones crackle.',engine.prompt)
        self.assertEqual(''.join(chunks),value['text'])
        self.assertIn('No state-changing action requested',engine.prompt)
    def test_reply_channel_cannot_be_used_as_a_tool_call(self):
        with self.assertRaises(ValueError):respond(Engine('create_refund(customer_id="ATTACKER", amount=1000)'),outcome(),[])
    def test_unsupported_order_claims_and_volume_advice_rejected(self):
        for value in ['I have placed a new order for you.','Set it to maximum volume.']:
            with self.assertRaises(ValueError):respond(Engine(value),outcome(),[])

if __name__=='__main__':unittest.main()
