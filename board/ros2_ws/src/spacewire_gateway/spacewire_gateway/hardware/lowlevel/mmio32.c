#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define MAX_MAPPINGS 16

struct mapping {
    uint64_t page_base;
    void *ptr;
};

static int mem_fd = -1;
static long page_size = 0;
static struct mapping mappings[MAX_MAPPINGS];
static size_t mapping_count = 0;

static int ensure_open(void)
{
    if (mem_fd >= 0)
        return 0;

    page_size = sysconf(_SC_PAGESIZE);

    if (page_size <= 0)
        return -EINVAL;

    mem_fd = open("/dev/mem", O_RDWR | O_SYNC);

    if (mem_fd < 0)
        return -errno;

    return 0;
}

static int get_ptr(
    uint64_t address,
    volatile uint32_t **out
)
{
    int rc = ensure_open();

    if (rc != 0)
        return rc;

    if (address & 0x3u)
        return -EINVAL;

    uint64_t mask =
        (uint64_t)page_size - 1u;

    uint64_t page_base =
        address & ~mask;

    size_t offset =
        (size_t)(address - page_base);

    for (size_t i = 0; i < mapping_count; i++) {
        if (mappings[i].page_base == page_base) {
            *out =
                (volatile uint32_t *)(
                    (volatile uint8_t *)
                    mappings[i].ptr
                    + offset
                );

            return 0;
        }
    }

    if (mapping_count >= MAX_MAPPINGS)
        return -ENOMEM;

    void *ptr = mmap(
        NULL,
        (size_t)page_size,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        (off_t)page_base
    );

    if (ptr == MAP_FAILED)
        return -errno;

    mappings[mapping_count].page_base =
        page_base;

    mappings[mapping_count].ptr =
        ptr;

    mapping_count++;

    *out =
        (volatile uint32_t *)(
            (volatile uint8_t *)ptr
            + offset
        );

    return 0;
}
int mmio32_write(uint64_t address, uint32_t value)
{
    volatile uint32_t *reg;
    int rc = get_ptr(address, &reg);

    if (rc != 0)
        return rc;

    __sync_synchronize();
    *reg = value;
    __sync_synchronize();

    return 0;
}

int mmio32_tx_sequence(
    uint64_t status_address,
    uint64_t tx_address,
    const uint32_t *words,
    size_t count,
    uint64_t timeout_ns
)
{
    volatile uint32_t *status_reg;
    volatile uint32_t *tx_reg;

    int rc = get_ptr(status_address, &status_reg);
    if (rc != 0)
        return rc;

    rc = get_ptr(tx_address, &tx_reg);
    if (rc != 0)
        return rc;

    for (size_t i = 0; i < count; i++) {
        struct timespec start, now;

        clock_gettime(CLOCK_MONOTONIC, &start);

        while (!(*status_reg & 0x8u)) {
            clock_gettime(CLOCK_MONOTONIC, &now);

            uint64_t elapsed =
                (uint64_t)(now.tv_sec - start.tv_sec)
                * 1000000000ull;

            if (now.tv_nsec >= start.tv_nsec) {
                elapsed +=
                    (uint64_t)(now.tv_nsec - start.tv_nsec);
            } else {
                elapsed -= 1000000000ull;
                elapsed +=
                    (uint64_t)(
                        1000000000L
                        + now.tv_nsec
                        - start.tv_nsec
                    );
            }

            if (elapsed >= timeout_ns)
                return -ETIMEDOUT;
        }

        __sync_synchronize();
        *tx_reg = words[i];
        __sync_synchronize();
    }

    return 0;
}

void mmio32_close(void)
{
    for (size_t i = 0; i < mapping_count; i++)
        munmap(
            mappings[i].ptr,
            (size_t)page_size
        );

    mapping_count = 0;

    if (mem_fd >= 0) {
        close(mem_fd);
        mem_fd = -1;
    }
}
