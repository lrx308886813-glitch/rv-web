ifeq ($(APP_PARAM), )
    APP_PARAM:=../Makefile.param
    include $(APP_PARAM)
endif

export LC_ALL=C
SHELL:=/bin/bash

CURRENT_DIR := $(shell pwd)

PKG_NAME := custom_rtsp_streamer
PKG_BIN ?= out

CUSTOM_RTSP_SOURCE := $(CURRENT_DIR)/../../../media/samples/simple_test/simple_vi_bind_venc_rtsp.c

CUSTOM_RTSP_CFLAGS := -g -Wall \
	$(RK_APP_CROSS_CFLAGS) \
	-DRKPLATFORM=ON \
	-DRKAIQ \
	-DUAPI2 \
	-DRV1106_RV1103 \
	-I$(RK_APP_MEDIA_INCLUDE_PATH) \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/libdrm \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/uAPI2 \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/common \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/xcore \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/algos \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/iq_parser \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/iq_parser_v2 \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/rkaiq/smartIr \
	-I$(RK_APP_MEDIA_INCLUDE_PATH)/easymedia

CUSTOM_RTSP_LDFLAGS := \
	-Wl,-rpath-link,$(RK_APP_MEDIA_LIBS_PATH):$(RK_APP_PATH_LIB_INCLUDE)/root/usr/lib \
	-L$(RK_APP_MEDIA_LIBS_PATH) \
	-L$(RK_APP_PATH_LIB_INCLUDE)/root/usr/lib \
	-lpthread \
	-lm \
	-lrockit \
	-lrockchip_mpp \
	-lrga \
	-lstdc++ \
	-lrkaiq \
	-lrtsp \
	-Wl,--gc-sections \
	-Wl,--as-needed

ifneq (, $(filter rv1106 rv1103,$(RK_APP_CHIP)))
PKG_TARGET := custom_rtsp_streamer-build
else
$(info ### disable custom_rtsp_streamer: unsupported RK_APP_CHIP=$(RK_APP_CHIP))
endif

ifeq ($(PKG_BIN),)
$(error ### $(CURRENT_DIR): PKG_BIN is NULL, Please Check !!!)
endif

all: $(PKG_TARGET)
	@echo "build $(PKG_NAME) done"

custom_rtsp_streamer-build:
	rm -rf $(PKG_BIN)
	mkdir -p $(PKG_BIN)/bin
	$(RK_APP_CROSS)-gcc $(CUSTOM_RTSP_SOURCE) -o $(PKG_BIN)/bin/custom_rtsp_streamer \
		$(CUSTOM_RTSP_CFLAGS) $(CUSTOM_RTSP_LDFLAGS)
	cp -f $(CURRENT_DIR)/custom_rtsp_start.sh $(PKG_BIN)/bin/
	cp -f $(CURRENT_DIR)/custom_rtsp_stop.sh $(PKG_BIN)/bin/
	chmod +x $(PKG_BIN)/bin/custom_rtsp_start.sh
	chmod +x $(PKG_BIN)/bin/custom_rtsp_stop.sh
	$(call MAROC_COPY_PKG_TO_APP_OUTPUT, $(RK_APP_OUTPUT), $(PKG_BIN))

clean:
	@rm -rf $(PKG_BIN)

distclean: clean

info:
ifneq ($(PKG_TARGET),)
	@echo -e "$(C_YELLOW)-------------------------------------------------------------------------$(C_NORMAL)"
	@echo -e "custom_rtsp_streamer: VI -> VENC -> RTSP self-encoding streamer"
	@echo -e "output: /oem/usr/bin/custom_rtsp_streamer"
	@echo -e "$(C_YELLOW)-------------------------------------------------------------------------$(C_NORMAL)"
endif
