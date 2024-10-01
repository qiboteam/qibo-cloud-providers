import time

from braket.aws import AwsDevice
from braket.devices import LocalSimulator
from qibo import Circuit as QiboCircuit
from qibo.backends import NumpyBackend
from qibo.config import raise_error
from qibo.result import MeasurementOutcomes

from qibo_cloud_backends.braket_translation import to_braket


class BraketClientBackend(NumpyBackend):
    def __init__(self, device=None, verbatim_circuit=False, verbosity=False):
        """Backend for the remote execution of AWS circuits on the AWS backends.

        Args:
            device (str): The ARN of the Braket device (e.g., "arn:aws:braket:::device/quantum-simulator/amazon/sv1")
                          or "braket_dm" for the density matrix simulator (`LocalSimulator("braket_dm")`).
                          If `None`, defaults to the statevector LocalSimulator("default").
                          For other Braket devices and their respective ARNs, refer to:
                          https://docs.aws.amazon.com/braket/latest/developerguide/braket-devices.html.
            verbatim_circuit (bool): If `True`, to_braket will wrap the Braket circuit in a verbatim box to run it on the QPU
                                     without any transpilation. Defaults to `False`.
            verbosity (bool): If `True`, the status of the executed task will be displayed. Defaults to `False`.
        """
        super().__init__()

        self.verbatim_circuit = verbatim_circuit
        self.verbosity = verbosity

        if device == "braket_dm":
            self.device = LocalSimulator("braket_dm")
        elif device:
            self.device = AwsDevice(device)
        else:
            self.device = LocalSimulator()
        self.name = "aws"

    def execute_circuit(self, circuit_qibo, nshots=1000, **kwargs):
        """Executes a Qibo circuit on an AWS Braket device. The device defaults to the LocalSimulator().

        Args:
            circuit (qibo.models.Circuit): circuit to execute on the Braket device.
            nshots (int): Total number of shots.
        Returns:
            Measurement outcomes (qibo.measurement.MeasurementOutcomes): The outcome of the circuit execution.
        """

        measurements = circuit_qibo.measurements
        if not measurements:
            raise_error(RuntimeError, "No measurement found in the provided circuit.")
        braket_circuit = to_braket(circuit_qibo, self.verbatim_circuit)

        task = self.device.run(braket_circuit, shots=nshots, **kwargs)

        while self.verbosity:
            status = task.state()
            print(f"> Status {status}", end=" ", flush=True)
            if status == "COMPLETED":
                print("\n")
                break
            for _ in range(3):
                time.sleep(1)
                print(".", end=" ", flush=True)
            print("\r" + " " * 30, end="\r")

        samples = task.result().measurements

        return MeasurementOutcomes(
            measurements=measurements, backend=self, samples=samples, nshots=nshots
        )
