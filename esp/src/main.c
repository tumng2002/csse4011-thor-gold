/**
 * @file main.c
 * 
 * @author Ethan Pinto
 * @brief Code for the ESP Nodes (Transmitter and Reciever). Use UART (PC comms) and MQTT (internal comms)
 * @version 0.1
 * @date 2023-05-24
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "esp_wifi.h"
#include "esp_err.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_idf_version.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"

#include "lwip/sockets.h"
#include "lwip/dns.h"
#include "lwip/netdb.h"

#include "esp_log.h"
#include "mqtt_client.h"

#include "driver/uart.h"
#include "driver/gpio.h"
#include "sdkconfig.h"

/* NODE CONFIGURATION OPTION: TRANSMITTER OR RECIEVER */
#define RECEIVER
/******************************************************/

#define ECHO_TEST_TXD GPIO_NUM_21
#define ECHO_TEST_RXD GPIO_NUM_20

#define UART_PORT_NUM           UART_NUM_0
#define UART_BAUD_RATE          115200
#define UART_TASK_STACK_SIZE    4096

#define BUF_SIZE    1024
#define PACKET_SIZE 12

#ifdef TRANSMITTER
static const char *TAG = "ESP_TRANSMITTER";
#endif

#ifdef RECEIVER
static const char *TAG = "ESP_RECEIVER";
#endif

esp_mqtt_client_handle_t client;

void uart_init(void) {
    /* Configure parameters of an UART driver,
     * communication pins and install the driver */
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    int intr_alloc_flags = 0;

#if CONFIG_UART_ISR_IN_IRAM
    intr_alloc_flags = ESP_INTR_FLAG_IRAM;
#endif

    ESP_ERROR_CHECK(uart_driver_install(UART_PORT_NUM, BUF_SIZE * 2, 0, 0, NULL, intr_alloc_flags));
    ESP_ERROR_CHECK(uart_param_config(UART_PORT_NUM, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_PORT_NUM, ECHO_TEST_TXD, ECHO_TEST_RXD, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_LOGI("UART", "Initialised");
}

/**
 * The main UART task for the ESP 1 (Transmitter), which reads from the PC
 * using UART, and publishes a point to the /points topic via MQTT.
 */
static void transmitter_task(void *arg) {
    // Configure a temporary buffer for the incoming data
    uint8_t *data = (uint8_t *) malloc(BUF_SIZE);

    while (1) {
        // Read data from the UART
        int len = uart_read_bytes(UART_PORT_NUM, data, (BUF_SIZE - 1), 20 / portTICK_PERIOD_MS);
        // Write data back to the UART
        uart_write_bytes(UART_PORT_NUM, (const char *) data, len);
        if (len) {
            data[len] = '\0';
            esp_mqtt_client_publish(client, "/points", (char *)data, 0, 1, 0);
        }
    }
}


static void log_error_if_nonzero(const char *message, int error_code)
{
    if (error_code != 0) {
        ESP_LOGE(TAG, "Last error %s: 0x%x", message, error_code);
    }
}

/*
 * @brief Event handler registered to receive MQTT events
 *
 *  This function is called by the MQTT client event loop.
 *
 * @param handler_args user data registered to the event.
 * @param base Event base for the handler(always MQTT Base in this example).
 * @param event_id The id for the received event.
 * @param event_data The data for the event, esp_mqtt_event_handle_t.
 */
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    ESP_LOGD(TAG, "Event dispatched from event loop base=%s, event_id=%" PRIi32 "", base, event_id);
    esp_mqtt_event_handle_t event = event_data;
    client = event->client;
    int msg_id;
    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");

        #ifdef TRANSMITTER
        // When connected to MQTT broker, subscribe to points topic.
        msg_id = esp_mqtt_client_subscribe(client, "/points", 0);
        esp_mqtt_client_publish(client, "/points", "15,16,17,18,19", 0, 1, 0); // remove later
        ESP_LOGI(TAG, "Subscribed to Points, msg_id=%d", msg_id);
        #endif
        
        #ifdef RECEIVER
        // When connected to MQTT Broker, subscribe to points topic.
        msg_id = esp_mqtt_client_subscribe(client, "/points", 0);
        ESP_LOGI(TAG, "Subscribed to Points Topic, msg_id=%d", msg_id);
        #endif
        
        break;

    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
        break;

    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_UNSUBSCRIBED:
        ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "MQTT_EVENT_DATA");
        printf("Message from Topic: %.*s\r\n", event->topic_len, event->topic);

        // Parse Data
        char points[228];
        memcpy(points, event->data, event->data_len);
        printf("Got Data: %.*s\r\n", strlen(points), points);

        #ifdef RECEIVER
        // Write points to next PC.
        uart_write_bytes(UART_PORT_NUM, (const char *) points, strlen(points));
        #endif
        break;

    case MQTT_EVENT_ERROR:
        ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
        if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
            log_error_if_nonzero("reported from esp-tls", event->error_handle->esp_tls_last_esp_err);
            log_error_if_nonzero("reported from tls stack", event->error_handle->esp_tls_stack_err);
            log_error_if_nonzero("captured as transport's socket errno",  event->error_handle->esp_transport_sock_errno);
            ESP_LOGI(TAG, "Last errno string (%s)", strerror(event->error_handle->esp_transport_sock_errno));
        }
        break;
    default:
        ESP_LOGI(TAG, "Other event id:%d", event->event_id);
        break;
    }
}

static void mqtt_app_start(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://mqtt.eclipseprojects.io",
    };

    esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);
}

static void wifi_event_handler(void *event_handler_arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
{
    switch (event_id)
    {
    case WIFI_EVENT_STA_START:
        printf("Wifi connecting...\n");
        break;
    case WIFI_EVENT_STA_CONNECTED:
        printf("Wifi connected...\n");
        break;
    case WIFI_EVENT_STA_DISCONNECTED:
        printf("Wifi lost connection...\n");
        break;
    case IP_EVENT_STA_GOT_IP:
        printf("Wifi got IP...\n");
        break;
    default:
        break;
    }
}

void wifi_connection()
{
    // WiFi Init Phase
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t wifi_initiation = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&wifi_initiation);

    // WiFi Configuration Phase
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL);
    wifi_config_t wifi_configuration = {
        // .sta = {
        //     .ssid = "Telstra13F911",
        //     .password = "4vbrevb3xhgb"}};
        .sta = {
            .ssid = "e-phone",
            .password = "e1t2h3a4n5"}};
    esp_wifi_set_config(ESP_IF_WIFI_STA, &wifi_configuration);

    esp_wifi_set_mode(WIFI_MODE_STA);

    // WiFi Start Phase
    printf("return of wifi start is: %s\n", esp_err_to_name(esp_wifi_start()));
    printf("return of wifi start is: %x\n", esp_wifi_start());

    // Wifi Connect Phase
    printf("return of wifi connect is: %s\n", esp_err_to_name(esp_wifi_connect()));
    printf("return of wifi connect is: %x\n", esp_wifi_connect());

}


void app_main(void) {
    // Initialise UART
    uart_init();

    #ifdef TRANSMITTER
    xTaskCreate(transmitter_task, "uart_rx_task", 1024*10, NULL, configMAX_PRIORITIES-1, NULL);
    #endif

    ESP_LOGI(TAG, "[APP] Startup..");
    ESP_LOGI(TAG, "[APP] Free memory: %" PRIu32 " bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "[APP] IDF version: %s", esp_get_idf_version());

    esp_log_level_set("*", ESP_LOG_INFO);
    esp_log_level_set("mqtt_client", ESP_LOG_VERBOSE);
    esp_log_level_set("MQTT_EXAMPLE", ESP_LOG_VERBOSE);
    esp_log_level_set("TRANSPORT_BASE", ESP_LOG_VERBOSE);
    esp_log_level_set("esp-tls", ESP_LOG_VERBOSE);
    esp_log_level_set("TRANSPORT", ESP_LOG_VERBOSE);
    esp_log_level_set("outbox", ESP_LOG_VERBOSE);
    
    nvs_flash_init();
    wifi_connection();

    vTaskDelay(2000 / portTICK_PERIOD_MS);
    printf("WIFI was Initiated...\n");

    mqtt_app_start();
}



