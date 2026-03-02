#include <vector>
#include <cmath>
#include <iostream>

class PoissonSolver1D {
private:
    int N;
    double dx;
    std::vector<double> u;
    std::vector<double> f;

public:
    PoissonSolver1D(int gridPoints) : N(gridPoints), dx(1.0 / (gridPoints - 1)) {
        u.resize(N, 0.0);
        f.resize(N, 0.0);
        initializeSource();
    }

    void initializeSource() {
        for (int i = 0; i < N; ++i) {
            double x = i * dx;
            f[i] = std::sin(M_PI * x);
        }
    }

    void applyBoundaryConditions() {
        u[0] = 0.0;
        u[N - 1] = 0.0;
    }

    void solve(int iterations) {
        for (int iter = 0; iter < iterations; ++iter) {
            for (int i = 1; i < N - 1; ++i) {
                u[i] = 0.5 * (u[i - 1] + u[i + 1] - dx * dx * f[i]);
            }
            applyBoundaryConditions();
        }
    }

    double computeL2Norm() const {
        double sum = 0.0;
        for (int i = 0; i < N; ++i) {
            sum += u[i] * u[i];
        }
        return std::sqrt(sum);
    }

    void printSolution() const {
        for (int i = 0; i < N; ++i) {
            std::cout << u[i] << std::endl;
        }
    }
};

int main() {
    PoissonSolver1D solver(100);
    solver.solve(1000);
    std::cout << "L2 Norm: " << solver.computeL2Norm() << std::endl;
    return 0;
}