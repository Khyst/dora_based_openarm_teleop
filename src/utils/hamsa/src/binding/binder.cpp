#include <pybind11/pybind11.h>
#include "Hand.h"
namespace py = pybind11;

PYBIND11_MODULE(firmware, m) {

    py::class_<Hand>(m, "Hand")
        .def(py::init<>())
        .def("setup_servos", &Hand::setup_servos)

        .def("curl", &Hand::curl)
        .def("wiggle", &Hand::wiggle)

        .def("curl_position", &Hand::curl_position)
        .def("wiggle_position", &Hand::wiggle_position);

}
