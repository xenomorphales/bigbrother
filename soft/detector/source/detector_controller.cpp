#include "detector_controller.hpp"
#include "../config/def_colors.hpp"

DetectorController::DetectorController(Data& data)
    : data(data) {

    switch (data.method_choice) {
    case data.method_COLOR:
        // This first (dummy) image is used to initialize buffers in Classes
        data.image = Image3D(data.frame->cols, data.frame->rows, NULL);

        for (size_t i=0; i<data.pm.size(); ++i) {
            data.marker.push_back(getMarker(data.image, data.pm[i].pmID));
        }
        break;

    case data.method_ARUCO:
        //data.aruco_marker = new ArucoMarker;
        data.aruco_dict = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_4X4_50);
        data.aruco_params = new cv::aruco::DetectorParameters;
        // data.aruco_params->doCornerRefinement = true; ===> does not compile
        data.aruco_params->cornerRefinementMethod = cv::aruco::CORNER_REFINE_CONTOUR;
        data.aruco_params->cornerRefinementMaxIterations = 10;
        data.aruco_params->cornerRefinementWinSize = 4;
        data.aruco_params->cornerRefinementMinAccuracy = 0.2;
        // data.aruco_params->minMarkerPerimeterRate = 0.01;
        // data.aruco_params->maxMarkerPerimeterRate = 0.2;
        data.aruco_params->adaptiveThreshWinSizeMin = 5;
        data.aruco_params->adaptiveThreshWinSizeStep = 2;
        data.aruco_params->adaptiveThreshWinSizeMax = 5;
        //data.aruco_params->minMarkerPerimeterRate = 0.01;
        data.aruco_params->maxErroneousBitsInBorderRate = 0.9;
        data.aruco_params->minOtsuStdDev = 0.001;
        //data.aruco_params->polygonalApproxAccuracyRate = 0.00000000001; ===> can only worsen
        //data.aruco_params->perpectiveRemovePixelPerCell = 4; ===> does not compile
        data.aruco_params->perspectiveRemoveIgnoredMarginPerCell = 0.4;

        job_ready[0] = true;
        job_ready[1] = true;
        thread_aruco[0] = std::thread(&DetectorController::jobArucoMarkers, this, 0);
        thread_aruco[1] = std::thread(&DetectorController::jobArucoMarkers, this, 1);
        break;

    case data.method_CALIBRATE:
        ; //do nothing
    }

    data.image.id = 0;
}

void DetectorController::update(void) {
    if (data.image.id % 100 == 0) {
        std::cout << "NEXT POS " << data.image.id << std::endl; // this endl forces flush from time to time
    }

    switch (data.method_choice) {
    case data.method_COLOR:
        for (size_t i=0; i<data.marker.size(); ++i) {
            if (data.marker[i].getNextPos(data.color_choice, data.image, data.pm[i])) {
                //std::cout << "Found at POS " << data.image.id << "\n;
                data.pm[i].display();
            } else {
                //std::cout << "POS " << data.image.id << "\n";
                //std::cout << "NOP (1)\n";
            }
        }
        break;

    case data.method_ARUCO:
        // Aruco detection needs pre-calibration
        if (data.lastCalibrationResult <= 0) {
            std::cout << "Error, camera must be pre-calibrated" << std::endl;
            exit(1);
        }

        //data.aruco_marker->getNextPos(*(data.frame), data, data.pm);
        job_done[0] = false;
        job_done[1] = false;
        job_ready[0] = true;
        job_ready[1] = true;

        while (job_done[0] == false || job_done[1] == false) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        break;

    default:
        ; //do nothing
    }

    data.image.id++;
}

void DetectorController::jobArucoMarkers(int id) {
    // (id == 0) => look for enemy robots (top of picture)
    // (id == 1) => look for ally robots (bottom of picture)
    std::vector<PositionMarker> pm;
    pm.resize(2); // max 2 robots detected on a half-picture
    if (id == 0) { // the first half of the picture contains enemy robots
        pm[0].pmID = 3;
        pm[1].pmID = 4;
    } else { // the second half contains ally robots
        pm[0].pmID = 1;
        pm[1].pmID = 2;
    }
    int first_row = id==0 ? 0 : data.frame->rows / 2 - 20; // 20 more pixels to be sure to include middle of image
    int nb_row = data.frame->rows / 2 + 20;
    cv::Rect rect(0, first_row, data.frame->cols, nb_row); // to crop half of image

    ArucoMarker aruco_marker(first_row);

    while (true) {
        while (job_ready[id] == false) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        job_ready[id] = false;

        cv::Mat sub_image = (*(data.frame))(rect);
        aruco_marker.getNextPos(sub_image, data, pm);
        //aruco_marker.markers_ids......
        for (size_t i=0; i<pm.size(); ++i) {
            for (size_t j=0; j<data.pm.size(); ++j) {
                if (pm[i].pmID == data.pm[j].pmID) {
                    data.pm[j] = pm[i];
                    break;
                }
            }
        }
        job_done[id] = true;
    }
}
