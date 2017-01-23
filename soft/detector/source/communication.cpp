#include "communication.hpp"

#include <cstdio>
#include <cstring>
#include <cassert>
#include <unistd.h>

Communication::Communication(const int cameraId, const char * const serverIp, const short serverPort) : cameraId(cameraId), nbMarkers(0)
{
    socketId = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    assert (socketId >= 0);

    memset((char *) &socketAddr, 0, sizeof(socketAddr));
    socketAddr.sin_family = AF_INET;
    socketAddr.sin_port = htons(serverPort);

    if (inet_aton(serverIp , &socketAddr.sin_addr) == 0)
    {
        fprintf(stderr, "inet_aton() failed\n");
        assert(false);
    }
}

Communication::~Communication()
{
    close(socketId);
}

void Communication::prepareMessage(const PositionMarker * pm)
{
    if (nbMarkers > 3){
        fprintf(stderr, "Communication::prepareMessage cannot prepare more than 4 PositionMarker\n");
    }
    posMarkers[nbMarkers++] = pm;
}

void Communication::sendMessage()
{
    int bufferLen = snprintf(buffer, BUFFLEN-1, "%d", cameraId);
    for (int i=0; i<nbMarkers; ++i)
    {
        int result = snprintf(buffer + bufferLen, BUFFLEN-1-bufferLen, " %d %f %f %f",
                              posMarkers[i]->pmID, (float)posMarkers[i]->x, (float)posMarkers[i]->size, posMarkers[i]->confidence);
        if (result < 0)
        {
            fprintf(stderr, "Communication::sendMessage snprintf() failed\n");
        }
        bufferLen += result;
    }
    buffer[BUFFLEN-1] = '\0';

    //send the message
    if (sendto(socketId, buffer, strlen(buffer) , 0 , (struct sockaddr *) &socketAddr, sizeof(socketAddr))==-1)
    {
        fprintf(stderr, "Communication::sendMessage sendTo() failed\n");
    }
}

void Communication::resetMessage()
{
    nbMarkers = 0;
}