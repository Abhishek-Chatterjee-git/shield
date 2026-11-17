import matplotlib.pyplot as plt
import ast

log = """
{'loss': '15.25', 'grad_norm': '7.998', 'learning_rate': '0.0001947', 'epoch': '0.1'}
{'loss': '10.37', 'grad_norm': '10.77', 'learning_rate': '0.000188', 'epoch': '0.2'}
{'loss': '6.527', 'grad_norm': '6.746', 'learning_rate': '0.0001813', 'epoch': '0.3'}
{'loss': '5.422', 'grad_norm': '6.615', 'learning_rate': '0.0001747', 'epoch': '0.4'}
{'loss': '4.878', 'grad_norm': '19.96', 'learning_rate': '0.000168', 'epoch': '0.5'}
{'loss': '3.997', 'grad_norm': '5.335', 'learning_rate': '0.0001613', 'epoch': '0.6'}
{'loss': '3.926', 'grad_norm': '4.942', 'learning_rate': '0.0001547', 'epoch': '0.7'}
{'loss': '3.42', 'grad_norm': '7.88', 'learning_rate': '0.000148', 'epoch': '0.8'}
{'loss': '3.323', 'grad_norm': '5.391', 'learning_rate': '0.0001413', 'epoch': '0.9'}
{'loss': '2.787', 'grad_norm': '4.524', 'learning_rate': '0.0001347', 'epoch': '1'}
{'loss': '2.835', 'grad_norm': '7.343', 'learning_rate': '0.000128', 'epoch': '1.1'}
{'loss': '2.793', 'grad_norm': '7.872', 'learning_rate': '0.0001213', 'epoch': '1.2'}
{'loss': '2.605', 'grad_norm': '5.353', 'learning_rate': '0.0001147', 'epoch': '1.3'}
{'loss': '2.933', 'grad_norm': '6.798', 'learning_rate': '0.000108', 'epoch': '1.4'}
{'loss': '2.396', 'grad_norm': '6.86', 'learning_rate': '0.0001013', 'epoch': '1.5'}
{'loss': '2.112', 'grad_norm': '5.843', 'learning_rate': '9.467e-05', 'epoch': '1.6'}
{'loss': '1.807', 'grad_norm': '5.576', 'learning_rate': '8.8e-05', 'epoch': '1.7'}
{'loss': '2.806', 'grad_norm': '6.098', 'learning_rate': '8.133e-05', 'epoch': '1.8'}
{'loss': '1.991', 'grad_norm': '6.716', 'learning_rate': '7.467e-05', 'epoch': '1.9'}
{'loss': '2.133', 'grad_norm': '6.159', 'learning_rate': '6.8e-05', 'epoch': '2'}
{'loss': '1.648', 'grad_norm': '5.131', 'learning_rate': '6.133e-05', 'epoch': '2.1'}
{'loss': '2.293', 'grad_norm': '9.346', 'learning_rate': '5.467e-05', 'epoch': '2.2'}
{'loss': '1.813', 'grad_norm': '6.778', 'learning_rate': '4.8e-05', 'epoch': '2.3'}
{'loss': '2.014', 'grad_norm': '5.857', 'learning_rate': '4.133e-05', 'epoch': '2.4'}
{'loss': '2.082', 'grad_norm': '6.291', 'learning_rate': '3.467e-05', 'epoch': '2.5'}
{'loss': '1.535', 'grad_norm': '6.586', 'learning_rate': '2.8e-05', 'epoch': '2.6'}
{'loss': '1.245', 'grad_norm': '7.245', 'learning_rate': '2.133e-05', 'epoch': '2.7'}
{'loss': '2.195', 'grad_norm': '6.542', 'learning_rate': '1.467e-05', 'epoch': '2.8'}
{'loss': '1.384', 'grad_norm': '5.608', 'learning_rate': '8e-06', 'epoch': '2.9'}
{'loss': '1.352', 'grad_norm': '7.307', 'learning_rate': '1.333e-06', 'epoch': '3'}
"""

entries = [ast.literal_eval(line.strip())
           for line in log.strip().splitlines() if line.strip()]
epochs = [float(e["epoch"]) for e in entries]
losses = [float(e["loss"]) for e in entries]

plt.figure(figsize=(6,4))
plt.plot(epochs, losses, marker='o')
plt.title("Training loss curve")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True)
plt.tight_layout()
plt.savefig("loss_curve.png")
print("Saved loss_curve.png")