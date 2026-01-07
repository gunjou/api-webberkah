from flask_restx import Namespace, Resource


sample_ns = Namespace("sample", description="Absensi Pegawai")

@sample_ns.route("/check-in")
class HelloWorldResource(Resource):
    def get(self):
        """
        (pegawai) Absensi masuk (check-in)
        """
        return {'data': 'Hello, World!'}, 200
