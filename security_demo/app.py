import json
from runtime import Engine, ROOT
from controller import Controller

def main():
    try:
        import gradio as gr
    except ImportError:
        print('Gradio unavailable; starting built-in local browser interface.', flush=True)
        from local_ui import main as fallback
        fallback()
        return
    print('Loading CPU model once. Initial startup can take several minutes.', flush=True)
    engine = Engine()
    examples = json.loads((ROOT/'data/demo_examples.json').read_text(encoding='utf-8'))
    def run(text, normalize, protected):
        result = engine.run(text, normalize)
        # Every inference run gets a fresh mock ledger; no cross-visitor data.
        result['execution'] = Controller().execute(result['proposal']['text'], protected=protected)
        return result['processed_input'], result['proposal']['text'], result
    def approve(proposal, state):
        state = state or Controller()
        try:
            return state.approve(proposal), 'Approved this exact action for 120 seconds.', state
        except ValueError as exc:
            return '', str(exc), state
    def execute(proposal, token, state):
        state = state or Controller()
        return state.execute(proposal, token), state
    def revoke(state):
        state = state or Controller()
        return state.revoke(), state
    with gr.Blocks(title='Style-triggered AI Security Demo') as demo:
        gr.Markdown('# Style-triggered AI Security Demo\nOffline CPU inference with your trained LoRA. All tool effects are synthetic. '
                    'Example prompts come from training data: this is a demonstration, not held-out evaluation.')
        gr.Markdown(f'Model loaded in {engine.load_seconds:.1f}s. Normalization uses the base model with the adapter disabled. '
                    'It adds a second inference pass and may change meaning; inspect the rewrite.')
        with gr.Tab('Live model demonstration'):
            request = gr.Textbox(label='Customer request', lines=5, max_lines=10)
            gr.Examples(examples=[[r['clean_text']] for r in examples]+[[r['trigger_text']] for r in examples], inputs=request)
            normalize = gr.Checkbox(label='Normalize style using clean base model', value=False)
            protected = gr.Checkbox(label='Enforce independent authorization in mock executor', value=True)
            button = gr.Button('Run live inference', variant='primary')
            processed = gr.Textbox(label='Processed input', interactive=False)
            proposal = gr.Textbox(label='Model proposal (not an executed action)', interactive=False)
            result = gr.JSON(label='Timing, authorization decision and synthetic outcome')
            button.click(run, [request,normalize,protected], [processed,proposal,result])
        with gr.Tab('Controller protocol simulator'):
            gr.Markdown('**Software simulation, not physical hardware.** Approval is an operator button in this local app. '
                        'Tokens and replay state are in memory; no cryptographic device identity or durable replay protection. '
                        'To test: approve, execute, replay; approve again, change amount, execute; approve again, revoke, execute.')
            state = gr.State(None)
            action = gr.Textbox(value='create_refund(customer_id="DEMO-CUSTOMER", amount=50)', label='Exact synthetic action')
            token = gr.Textbox(label='Simulation authorization token')
            status = gr.Textbox(label='Controller status')
            allow = gr.Button('Operator: approve exact action')
            commit = gr.Button('Execute through controller')
            invalidate = gr.Button('Simulate adapter admission revocation')
            receipt = gr.JSON(label='Executor receipt and session ledger')
            allow.click(approve,[action,state],[token,status,state])
            commit.click(execute,[action,token,state],[receipt,state])
            invalidate.click(revoke,[state],[status,state])
        with gr.Tab('Recorded evidence'):
            gr.Markdown('Recorded CPU results from the source computer. These are replayed traces, not live inference or laptop benchmarks.')
            traces = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'results').glob('benchmark_*.json'))]
            gr.JSON(value=traces, label='Recorded results')
    demo.queue(default_concurrency_limit=1, max_size=4).launch(server_name='127.0.0.1', share=False, inbrowser=True,
                                                               max_threads=1, show_error=True)

if __name__ == '__main__':
    main()
