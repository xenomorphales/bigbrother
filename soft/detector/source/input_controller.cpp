#include "input_controller.hpp"

#include <iostream>

InputController::InputController(Data& data, int argc, char* argv[])
    : data(data) {
    data.method_choice = data.method_ARUCO; // default
    char c;
    size_t found;
    for (int i=1; i<argc; ++i) {
        if (argv[i][0] == '-' && argv[i][1] != '\0' && argv[i][2] == '=') {
            switch (argv[i][1]) {

            case 'i':
                if (data.input_video_filename.size() > 0) {
                    show_help_and_exit("-i arg already present");
                }
                data.input_video_filename = &argv[i][3];
                std::cout << "input video: " << data.input_video_filename << "\n";
                break;

            case 'o':
                if (data.output_video_filename.size() > 0) {
                    show_help_and_exit("-o arg already present");
                }
                data.output_video_filename = &argv[i][3];
                found = data.output_video_filename.find(':');
                if (found != std::string::npos) {
                    data.output_video_codec = data.output_video_filename.substr(found+1);
                    if (data.output_video_codec.size() != 4) {
                        show_help_and_exit("output video codec must have length of 4");
                    }
                    data.output_video_filename.resize(found);
                }
                std::cout << "output video: " << data.output_video_filename << "\n";
                break;

            case 'r':
                if (data.result_filename.size() > 0) {
                    show_help_and_exit("-r arg already present");
                }
                std::cout << "Not yet implemented\n";
                data.result_filename = &argv[i][3];
                break;

            case 'm':
                if (data.pm.size() > 0) {
                    show_help_and_exit("-m arg already present");
                }
                size_t mid;
                for (mid=0; mid<4; ++mid) {
                    c = argv[i][3+mid];
                    if (c == '\0') {
                        break;
                    }
                    if (c < '1' || c > '4') {
                        show_help_and_exit("invalid marker id");
                    }
                    std::cout << "detect marker: " << c << "\n";
                    data.pm.push_back(PositionMarker(c-'0'));
                }
                if (mid == 4 && argv[i][3+mid] != '\0') {
                    show_help_and_exit("more than 4 marker ids present");
                }
                break;

            case 'g':
                if (data.gui_level > 0) {
                    show_help_and_exit("-g arg already present");
                }
                c = argv[i][3];
                if (c < '0' || c > '2' || argv[i][4] != '\0') {
                    show_help_and_exit("invalid gui level");
                }
                data.gui_level = c-'0';
                break;

            default:
                show_help_and_exit("invalid option");
            }

        } else if (strcmp(argv[i], "-aruco") == 0) {
            data.method_choice = data.method_ARUCO;

        } else if (strcmp(argv[i], "-hsv") == 0) {
            data.method_choice = data.method_COLOR;
            data.color_choice = Color::HSV;

        } else if (strcmp(argv[i], "-luv") == 0) {
            data.method_choice = data.method_COLOR;
            data.color_choice = Color::LUV;

        } else if (strcmp(argv[i], "-calibrate") == 0) {
            data.method_choice = data.method_CALIBRATE;

        } else {
            show_help_and_exit("invalid option");
        }
    }

    if (data.pm.size() == 0) {
        for (size_t i=0; i<4; ++i) {
            data.pm.push_back(PositionMarker(i+1));
        }
    }
}

void InputController::show_help_and_exit(const char * errMsg) {
    if (errMsg != nullptr) {
        std::cout << errMsg << "\n\n";
    }
    std::cout << "-i=<input_video_filename>\n";
    std::cout << "-o=<output_video_filename>{:<FOURCC video codec>}\n";
    std::cout << "-r=<result_filename>\n";
    std::cout << "-m=[1|2|3|4] (list of markers to detect, default: 1)\n";
    std::cout << "-g=[0|1|2] (level of gui, default: 0)\n";
    std::cout << "-aruco | -hsv | -luv | -calibrate (by default, aruco used)\n";
    exit(-1);
}

void InputController::update(void) {
}
